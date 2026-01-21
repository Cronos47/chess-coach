import { useState } from "react";

interface Props {
    disabled: boolean;
    onNewGame: (
        side: "white" | "black",
        difficulty: string,
        verbosity: number
    ) => void;
    onUndo: () => void;
}

export default function ControlsBar({
    disabled,
    onNewGame,
    onUndo,
}: Props) {
    const [side, setSide] = useState<"white" | "black">("white");
    const [difficulty, setDifficulty] = useState("medium");
    const [verbosity, setVerbosity] = useState(2);

    return (
        <div className="controls-bar">
            <div className="control-group">
                <label>Side</label>
                <select
                    value={side}
                    disabled={disabled}
                    onChange={(e) => setSide(e.target.value as any)}
                >
                    <option value="white">White</option>
                    <option value="black">Black</option>
                </select>
            </div>

            <div className="control-group">
                <label>Bot</label>
                <select
                    value={difficulty}
                    disabled={disabled}
                    onChange={(e) => setDifficulty(e.target.value)}
                >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                </select>
            </div>

            <div className="control-group">
                <label>Coach</label>
                <select
                    value={verbosity}
                    disabled={disabled}
                    onChange={(e) => setVerbosity(Number(e.target.value))}
                >
                    <option value={1}>Short</option>
                    <option value={2}>Normal</option>
                    <option value={3}>Verbose</option>
                </select>
            </div>

            <button disabled={disabled} onClick={() => onNewGame(side, difficulty, verbosity)}>
                New Game
            </button>

            <button disabled={disabled} onClick={onUndo}>
                Undo
            </button>
        </div>
    );
}
