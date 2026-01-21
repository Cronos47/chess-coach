from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_new_game_and_get_state():
    # Start a new game
    r = client.post("/api/new_game", json={"side": "white", "bot_difficulty": "easy", "coach_verbosity": 2})
    assert r.status_code == 200
    data = r.json()
    assert "state" in data
    assert data["state"]["side_to_move"] == "white"
    assert data["state"]["move_list"] == []
    assert data["state"]["game_over"] is False

    # Fetch state
    r2 = client.get("/api/state")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["state"]["fen"] == data["state"]["fen"]
    assert data2["state"]["move_list"] == []
