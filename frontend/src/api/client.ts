import { GameState, AgentOutput } from "../state/types";

const API_BASE = "http://localhost:8000";

async function jsonOrThrow(r: Response) {
    if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `Request failed (${r.status})`);
    }
    return r.json();
}

export async function fetchState(): Promise<{
    state: GameState;
    agent_output?: AgentOutput;
}> {
    const r = await fetch(`${API_BASE}/api/state`);
    return jsonOrThrow(r);
}

export async function newGame(
    side: "white" | "black",
    difficulty: string,
    verbosity: number
): Promise<{ state: GameState; agent_output?: AgentOutput }> {
    const r = await fetch(`${API_BASE}/api/new_game`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            side,
            bot_difficulty: difficulty,
            coach_verbosity: verbosity,
        }),
    });
    return jsonOrThrow(r);
}

export async function sendMove(
    uciMove: string,
    thinkTimeMs: number | null,
    selfReport?: string | null
): Promise<{ state: GameState; agent_output?: AgentOutput }> {
    const r = await fetch(`${API_BASE}/api/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            uci_move: uciMove,
            think_time_ms: thinkTimeMs,
            self_report: selfReport ?? null,
        }),
    });
    return jsonOrThrow(r);
}

export async function undoMove(): Promise<{ state: GameState; agent_output?: AgentOutput }> {
    const r = await fetch(`${API_BASE}/api/undo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
    });
    return jsonOrThrow(r);
}

/**
 * WebSocket connection (optional enhancement).
 * The UI should NOT rely on this for correctness—REST responses update the UI already.
 */
export function connectWS(onMessage: (data: any) => void): WebSocket {
    const ws = new WebSocket("ws://localhost:8000/ws/game");

    ws.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            onMessage(data);
        } catch {
            // ignore malformed payloads
        }
    };

    ws.onerror = () => {
        // Keep quiet; REST remains the source of truth
    };

    return ws;
}
