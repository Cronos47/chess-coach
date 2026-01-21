# Agentic Chess Coach

A local, production-quality **Agentic Chess Coach** web app.

You play chess against **Stockfish**. After each of your moves, an **LLM-powered agent** provides:
- **Chess coaching** (engine-grounded, actionable)
- **Mental state assessment** (game-related only, non-medical)
- **Position analysis** (eval, threats, plans)

The app runs **entirely locally** (except OpenAI API) with:
- FastAPI backend
- WebSocket updates
- React + TypeScript frontend
- Stockfish via python-chess (UCI)

---

## Features

- Interactive chessboard (drag/drop or click-to-move)
- Legal move validation
- Bot difficulty (easy / medium / hard)
- Coach verbosity (short / normal / verbose)
- Undo (before bot move)
- Move list, captured pieces, simple clocks
- Live coaching in 3 tabs:
  - Chess Coach
  - Mental Assessment
  - Position Analysis
- Mental signals:
  - Think time per move
  - Blunder streak
  - Rapid move after blunder
  - Undo attempts
  - Optional self-report (calm / tilted / tired / focused)

---

## Tech Stack

### Backend
- Python 3.10+
- FastAPI
- python-chess + Stockfish (UCI)
- LangChain (`create_agent`)
- OpenAI API
- WebSocket (real-time updates)

### Frontend
- React 18
- TypeScript
- Vite
- chess.js
- react-chessboard

---

## Prerequisites

python --version
# Py3 >= 3.10

## How to run
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

```bash
cd frontend
npm install
npm run dev
