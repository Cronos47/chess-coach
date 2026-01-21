import { useEffect, useMemo, useState } from "react";
import { Chess, Square } from "chess.js";
import { Chessboard } from "react-chessboard";

type Props = {
    fen: string; // ✅ source of truth for UI
    disabled: boolean;
    userSide: "white" | "black";
    onMoveStart: () => void;
    onMove: (uci: string) => void; // e2e4 etc
};

export default function ChessBoardPanel({
    fen,
    disabled,
    userSide,
    onMoveStart,
    onMove,
}: Props) {
    // Local chess.js instance ONLY for legal move highlighting + building UCI
    const chess = useMemo(() => {
        const c = new Chess();
        c.load(fen);
        return c;
    }, [fen]);

    const [selected, setSelected] = useState<Square | null>(null);
    const [legalTargets, setLegalTargets] = useState<Square[]>([]);

    useEffect(() => {
        // When fen changes (after a move), clear selection + highlights
        setSelected(null);
        setLegalTargets([]);
    }, [fen]);

    function selectSquare(sq: Square) {
        if (disabled) return;
        const piece = chess.get(sq);
        if (!piece) {
            setSelected(null);
            setLegalTargets([]);
            return;
        }

        // Enforce: user can only move their own pieces
        const userColor = userSide === "white" ? "w" : "b";
        if (piece.color !== userColor) return;

        setSelected(sq);
        const moves = chess.moves({ square: sq, verbose: true }) as any[];
        setLegalTargets(moves.map((m) => m.to as Square));
        onMoveStart();
    }

    function tryMove(from: Square, to: Square) {
        if (disabled) return;

        const moves = chess.moves({ square: from, verbose: true }) as any[];
        const match = moves.find((m) => m.to === to);

        if (!match) return;

        // Build UCI (promotion handled)
        const promotion = match.promotion ? match.promotion : undefined;
        const uci = `${from}${to}${promotion ?? ""}`;
        onMove(uci);
    }

    // Click-to-move support
    const onSquareClick = (sq: Square) => {
        if (disabled) return;

        if (!selected) {
            selectSquare(sq);
            return;
        }

        // If clicking selected again -> deselect
        if (sq === selected) {
            setSelected(null);
            setLegalTargets([]);
            return;
        }

        // If clicked a legal target -> move
        if (legalTargets.includes(sq)) {
            tryMove(selected, sq);
            return;
        }

        // Otherwise, treat it as selecting a different piece
        selectSquare(sq);
    };

    // Drag-drop support
    const onPieceDrop = (sourceSquare: Square, targetSquare: Square) => {
        if (disabled) return false;
        const piece = chess.get(sourceSquare);
        const userColor = userSide === "white" ? "w" : "b";
        if (!piece || piece.color !== userColor) return false;

        const moves = chess.moves({ square: sourceSquare, verbose: true }) as any[];
        const match = moves.find((m) => m.to === targetSquare);
        if (!match) return false;

        const promotion = match.promotion ? match.promotion : undefined;
        const uci = `${sourceSquare}${targetSquare}${promotion ?? ""}`;
        onMoveStart();
        onMove(uci);
        return true;
    };

    // Highlight legal target squares (react-chessboard style)
    const customSquareStyles: Record<string, React.CSSProperties> = {};
    for (const t of legalTargets) {
        customSquareStyles[t] = {
            background:
                "radial-gradient(circle, rgba(43,108,176,0.35) 30%, transparent 31%)",
            borderRadius: "50%",
        };
    }
    if (selected) {
        customSquareStyles[selected] = {
            outline: "3px solid rgba(43,108,176,0.8)",
            outlineOffset: "-3px",
        };
    }

    return (
        <div>
            <Chessboard
                // ✅ Key forces remount when fen changes; eliminates “needs refresh”
                key={fen}
                id="AgenticChessBoard"
                position={fen}
                boardOrientation={userSide}
                onSquareClick={onSquareClick}
                onPieceDrop={onPieceDrop}
                customSquareStyles={customSquareStyles}
                arePiecesDraggable={!disabled}
            />
        </div>
    );
}
