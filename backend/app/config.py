from pathlib import Path
from typing import Optional, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Centralized application configuration.

    All secrets MUST come from environment variables.
    """

    # OpenAI
    OPENAI_API_KEY: str

    # Stockfish
    STOCKFISH_PATH: Optional[str] = None

    # Defaults
    DEFAULT_BOT_DIFFICULTY: str = "medium"  # easy | medium | hard
    DEFAULT_COACH_VERBOSITY: int = 2        # 1 (short) - 3 (detailed)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()


def find_stockfish_binary() -> str:
    """
    Resolve Stockfish binary path.

    Priority:
    1. STOCKFISH_PATH env var
    2. Common OS install locations
    3. Raise clear error if not found
    """
    if settings.STOCKFISH_PATH:
        path = Path(settings.STOCKFISH_PATH)
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"STOCKFISH_PATH set but not found: {path}")

    common_paths: List[Path] = [
        # Linux
        Path("/usr/bin/stockfish"),
        Path("/usr/local/bin/stockfish"),
        # macOS (brew)
        Path("/opt/homebrew/bin/stockfish"),
        Path("/usr/local/Cellar/stockfish/bin/stockfish"),
        # Windows (common manual installs)
        Path("C:/Program Files/Stockfish/stockfish.exe"),
        Path("C:/stockfish/stockfish.exe"),
    ]

    for p in common_paths:
        if p.exists():
            return str(p)

    raise FileNotFoundError(
        "Stockfish binary not found. "
        "Install stockfish and/or set STOCKFISH_PATH env var."
    )
