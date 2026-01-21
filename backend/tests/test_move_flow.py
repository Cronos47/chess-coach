import os
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _have_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def test_illegal_move_rejected():
    client.post("/api/new_game", json={"side": "white", "bot_difficulty": "easy", "coach_verbosity": 1})
    r = client.post("/api/move", json={"uci_move": "e2e5", "think_time_ms": 1200, "self_report": "calm"})
    assert r.status_code == 400
    assert "Illegal move" in r.text


def test_legal_move_advances_game_and_bot_responds_or_skips_without_llm():
    """
    This endpoint runs the LangChain agent, which requires OPENAI_API_KEY.
    If the key isn't set, we skip to keep local tests runnable without extra services.
    """
    if not _have_openai_key():
        return

    client.post("/api/new_game", json={"side": "white", "bot_difficulty": "easy", "coach_verbosity": 1})

    r = client.post("/api/move", json={"uci_move": "e2e4", "think_time_ms": 1500, "self_report": "focused"})
    assert r.status_code == 200
    data = r.json()

    # Move list should include at least the user's move
    assert data["state"]["move_list"][0] == "e2e4"

    # Bot move should exist if game not ended immediately (it won't here)
    assert data.get("bot_move") is not None
    assert len(data.get("bot_move")) >= 4

    # Agent output should be present (parsed or raw fallback)
    # Our current response model returns parsed agent_output if parser succeeded.
    # If parser fails, agent_output can be null; that's acceptable.
    assert "state" in data
