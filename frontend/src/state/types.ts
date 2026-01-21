// ---------- GAME STATE ----------

export interface ClockState {
    white_ms: number;
    black_ms: number;
}

export interface SignalState {
    think_times_ms: number[];
    blunder_streak: number;
    undo_attempts: number;
    rapid_after_blunder: boolean;
    self_report?: string | null;
}

export interface GameState {
    fen: string;
    side_to_move: "white" | "black";
    move_list: string[];
    captured_pieces: {
        white: string[];
        black: string[];
    };
    clocks: ClockState;
    signals: SignalState;
    game_over: boolean;
    result?: string | null;
}

// ---------- AGENT OUTPUT ----------

export interface CoachOutput {
    move_quality: string;
    bullets: string[];
    pv?: string | null;
}

export interface MentalOutput {
    observed_signals: string[];
    inference: string;
    micro_reset_tip: string;
}

export interface PositionOutput {
    eval: string;
    why: string[];
    threats: string[];
    plans: {
        white: string[];
        black: string[];
    };
}

export interface AgentOutput {
    coach: CoachOutput;
    mental: MentalOutput;
    position: PositionOutput;
    raw_text?: string;
}
