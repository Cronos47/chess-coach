import { useState } from "react";
import { AgentOutput } from "../state/types";

interface Props {
    agentOutput: AgentOutput | null;
}

type TabKey = "coach" | "mental" | "position";

export default function TabsPanel({ agentOutput }: Props) {
    const [activeTab, setActiveTab] = useState<TabKey>("coach");

    if (!agentOutput) {
        return (
            <div className="tabs-panel">
                <div className="tabs-header">
                    <button className="active">Chess Coach</button>
                    <button>Mental</button>
                    <button>Position</button>
                </div>
                <div className="tab-content muted">
                    Make a move to get coaching feedback.
                </div>
            </div>
        );
    }

    return (
        <div className="tabs-panel">
            <div className="tabs-header">
                <button
                    className={activeTab === "coach" ? "active" : ""}
                    onClick={() => setActiveTab("coach")}
                >
                    Chess Coach
                </button>
                <button
                    className={activeTab === "mental" ? "active" : ""}
                    onClick={() => setActiveTab("mental")}
                >
                    Mental
                </button>
                <button
                    className={activeTab === "position" ? "active" : ""}
                    onClick={() => setActiveTab("position")}
                >
                    Position
                </button>
            </div>

            <div className="tab-content">
                {activeTab === "coach" && (
                    <>
                        <h3>Move Quality: {agentOutput.coach.move_quality}</h3>
                        <ul>
                            {agentOutput.coach.bullets.map((b, i) => (
                                <li key={i}>{b}</li>
                            ))}
                        </ul>
                        {agentOutput.coach.pv && (
                            <p>
                                <strong>PV:</strong> {agentOutput.coach.pv}
                            </p>
                        )}
                    </>
                )}

                {activeTab === "mental" && (
                    <>
                        <h3>Observed Signals</h3>
                        <ul>
                            {agentOutput.mental.observed_signals.map((s, i) => (
                                <li key={i}>{s}</li>
                            ))}
                        </ul>
                        <p>
                            <strong>Inference:</strong> {agentOutput.mental.inference}
                        </p>
                        <p>
                            <strong>Micro-reset:</strong>{" "}
                            {agentOutput.mental.micro_reset_tip}
                        </p>
                    </>
                )}

                {activeTab === "position" && (
                    <>
                        <p>
                            <strong>Eval:</strong> {agentOutput.position.eval}
                        </p>
                        <h4>Why</h4>
                        <ul>
                            {agentOutput.position.why.map((w, i) => (
                                <li key={i}>{w}</li>
                            ))}
                        </ul>

                        <h4>Immediate Threats</h4>
                        <ul>
                            {agentOutput.position.threats.map((t, i) => (
                                <li key={i}>{t}</li>
                            ))}
                        </ul>

                        <h4>Plans (White)</h4>
                        <ul>
                            {agentOutput.position.plans.white.map((p, i) => (
                                <li key={i}>{p}</li>
                            ))}
                        </ul>

                        <h4>Plans (Black)</h4>
                        <ul>
                            {agentOutput.position.plans.black.map((p, i) => (
                                <li key={i}>{p}</li>
                            ))}
                        </ul>
                    </>
                )}
            </div>
        </div>
    );
}
