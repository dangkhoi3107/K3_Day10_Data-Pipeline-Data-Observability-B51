"""Launcher script for Web UI Dashboard."""
import os
import sys
import webbrowser
from pathlib import Path

src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ui.server import start_server


def main():
    port = int(os.environ.get("PORT", 8080))
    url = f"http://localhost:{port}"
    print("================================================================")
    print(f"  🎨 DATA PIPELINE & OBSERVABILITY WEB DASHBOARD UI")
    print("================================================================")
    print(f"🌐 Server URL: {url}")
    print("💡 Bấm Ctrl+C để dừng Web Server.\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    start_server(port)

if __name__ == "__main__":
    main()
