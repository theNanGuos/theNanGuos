from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

def read(path: Path) -> str:
    prompt = path.read_text(encoding="utf-8")
    return prompt

def conductor() -> str:
    path = PROJECT_DIR / "prompts" / "conductor.md"
    return read(path)
    

def lyrics() -> str:
    path = PROJECT_DIR / "prompts" / "lyrics.md"
    return read(path)

def melody() -> str:
    path = PROJECT_DIR / "prompts" / "melody.md"
    return read(path)

def arrange() -> str:
    path  = PROJECT_DIR / "prompts" / "arrange.md"
    return read(path)