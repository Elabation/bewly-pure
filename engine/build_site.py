from pathlib import Path
from publish_discovery import rebuild

if __name__ == "__main__":
    print(rebuild(Path(__file__).resolve().parents[1]))
