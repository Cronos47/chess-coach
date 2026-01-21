import { useEffect, useRef, useState } from "react";
import { Chess } from "chess.js";

import { fetchState, newGame, sendMove, undoMove, connectWS } from "./api/client";
import { GameState, AgentOutput } from "./state/types";
import ChessBoardPanel from "./components/ChessBoardPanel";
import TabsPanel from "./components/TabsPanel";
import SignalsPanel from "./components/SignalsPanel";
import ControlsBar from "./components/ControlsBar";

export default function App() {
    const [fen, setFen] = useState(new Chess().fen());
    const [state, setState] = useState<GameState | null>(null);
    const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);

    // Shows “thinking…” so you know it’s processing
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState<string>("");

    const [playerSide, setPlayerSide] = useState<"white" | "black">("white");

    const wsRef = useRef<WebSocket | null>(null);
    const moveStartTime = useRef<number | null>(null);

    useEffect(() => {
        fetchState()
            .then((res) => {
                setState(res.state);
                setFen(res.state.fen);
                setAgentOutput(res.agent_output ?? null);
            })
            .catch(() => {
                // ignore; actions will error with alerts
            });

        // WS optional enhancement
        wsRef.current = connectWS((msg) => {
            if (msg.type === "update") {
                if (msg.state?.fen) {
                    setState(msg.state);
                    setFen(msg.state.fen);
                }
                if (msg.agent_output) setAgentOutput(msg.agent_output);
            }
        });

        return () => wsRef.current?.close();
    }, []);

    const handleUserMove = async (uci: string) => {
        if (busy) return;

        const prevFen = fen;

        // ✅ OPTIMISTIC: apply user move instantly locally
        try {
            const local = new Chess();
            local.load(prevFen);

            // chess.js needs “e2e4” or “e7e8q” style
            const from = uci.slice(0, 2) as any;
            const to = uci.slice(2, 4) as any;
            const promo = uci.length === 5 ? (uci[4] as any) : undefined;

            const moved = local.move({ from, to, promotion: promo });
            if (!moved) {
                // If local can't apply, don't send to backend
                alert("Illegal move (local validation)");
                return;
            }

            setFen(local.fen()); // ✅ immediate UI update
        } catch {
            alert("Invalid move format");
            return;
        }

        setBusy(true);
        setStatus("Your move sent… Bot/Coach thinking…");

        const thinkTime =
            moveStartTime.current !== null ? Date.now() - moveStartTime.current : null;

        try {
            const res = await sendMove(uci, thinkTime, state?.signals.self_report);

            // ✅ Backend authoritative reconciliation (includes bot move + final fen)
            setState(res.state);
            setFen(res.state.fen);
            setAgentOutput(res.agent_output ?? null);
            setStatus("");
        } catch (e: any) {
            // ✅ Rollback if backend rejects
            setFen(prevFen);
            setStatus("");
            alert(e?.message ?? "Move failed");
        } finally {
            moveStartTime.current = null;
            setBusy(false);
        }
    };

    const handleNewGame = async (
        side: "white" | "black",
        difficulty: string,
        verbosity: number
    ) => {
        if (busy) return;
        setBusy(true);
        setStatus("Starting new game…");

        try {
            setPlayerSide(side);
            const res = await newGame(side, difficulty, verbosity);

            setState(res.state);
            setFen(res.state.fen);
            setAgentOutput(res.agent_output ?? null);
            setStatus("");
        } catch (e: any) {
            setStatus("");
            alert(e?.message ?? "Failed to start new game");
        } finally {
            setBusy(false);
        }
    };

    const handleUndo = async () => {
        if (busy) return;
        setBusy(true);
        setStatus("Undoing…");
        try {
            const res = await undoMove();
            setState(res.state);
            setFen(res.state.fen);
            setAgentOutput(res.agent_output ?? agentOutput);
            setStatus("");
        } catch (e: any) {
            setStatus("");
            alert(e?.message ?? "Undo failed");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="app">
            <div className="left-panel">
                <div style={{ marginBottom: 8, minHeight: 20, fontSize: 14 }}>
                    {status ? status : ""}
                </div>

                <ChessBoardPanel
                    fen={fen}
                    disabled={busy}
                    userSide={playerSide}
                    onMoveStart={() => (moveStartTime.current = Date.now())}
                    onMove={handleUserMove}
                />

                <ControlsBar disabled={busy} onNewGame={handleNewGame} onUndo={handleUndo} />
            </div>

            <div className="right-panel">
                <SignalsPanel
                    signals={state?.signals}
                    onSelfReportChange={(v) =>
                        setState((s) =>
                            s ? { ...s, signals: { ...s.signals, self_report: v } } : s
                        )
                    }
                />
                <TabsPanel agentOutput={agentOutput} />
            </div>
        </div>
    );
}
