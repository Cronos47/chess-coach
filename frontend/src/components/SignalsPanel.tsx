import { SignalState } from "../state/types";

interface Props {
    signals?: SignalState;
    onSelfReportChange: (v: string) => void;
}

export default function SignalsPanel({ signals, onSelfReportChange }: Props) {
    if (!signals) {
        return (
            <div className="signals-panel muted">
                Signals will appear after your first move.
            </div>
        );
    }

    const avgThinkTime =
        signals.think_times_ms.length > 0
            ? Math.round(
                signals.think_times_ms.reduce((a, b) => a + b, 0) /
                signals.think_times_ms.length
            )
            : null;

    return (
        <div className="signals-panel">
            <h3>Signals</h3>

            <div className="signal-row">
                <label>Mood (self-report)</label>
                <select
                    value={signals.self_report ?? ""}
                    onChange={(e) => onSelfReportChange(e.target.value)}
                >
                    <option value="">—</option>
                    <option value="calm">Calm</option>
                    <option value="focused">Focused</option>
                    <option value="tilted">Tilted</option>
                    <option value="tired">Tired</option>
                </select>
            </div>

            <div className="signal-row">
                <strong>Avg think time:</strong>{" "}
                {avgThinkTime ? `${avgThinkTime} ms` : "—"}
            </div>

            <div className="signal-row">
                <strong>Blunder streak:</strong> {signals.blunder_streak}
            </div>

            <div className="signal-row">
                <strong>Undo attempts:</strong> {signals.undo_attempts}
            </div>

            <div className="signal-row">
                <strong>Rapid after blunder:</strong>{" "}
                {signals.rapid_after_blunder ? "Yes" : "No"}
            </div>
        </div>
    );
}
