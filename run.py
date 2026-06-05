#!/usr/bin/env python3
"""
AI Incident Commander — cross-platform CLI runner.

Usage:
    python run.py              Start the FastAPI server
    python run.py --setup      Install dependencies
    python run.py --test       Run regression tests
    python run.py --check      Verify environment
    python run.py --help       Show this message
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"


def _pip() -> str:
    if sys.platform == "win32":
        return str(VENV / "Scripts" / "pip.exe")
    return str(VENV / "bin" / "pip")


def _python() -> str:
    if sys.platform == "win32":
        return str(VENV / "Scripts" / "python.exe")
    return str(VENV / "bin" / "python")


def _uvicorn() -> str:
    if sys.platform == "win32":
        return str(VENV / "Scripts" / "uvicorn.exe")
    return str(VENV / "bin" / "uvicorn")


def cmd_install():
    if not VENV.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        print(f"Created virtual environment at {VENV}")
    subprocess.run([_pip(), "install", "-r", str(ROOT / "requirements.txt")], check=True)
    subprocess.run([_pip(), "install", "pytest", "pytest-asyncio"], check=True)
    print("All dependencies installed.")


def cmd_test():
    subprocess.run([_python(), "-m", "pytest", str(ROOT / "tests"), "-v"], check=True)


def cmd_check():
    print(f"Platform: {sys.platform}")
    print(f"Python:   {sys.executable}")
    print(f"Root:     {ROOT}")
    print(f"Venv:     {VENV.exists()}")
    req = ROOT / ".env"
    print(f".env:     {req.exists()}")
    if req.exists():
        has_key = "DEEPSEEK_API_KEY" in req.read_text()
        print(f"API key:  {'set' if has_key else 'MISSING'}")
    print(f"Tests:    {(ROOT / 'tests').exists()}")


def cmd_serve(args):
    uvicorn_args = [
        _uvicorn(),
        "app.main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]
    if args.reload:
        uvicorn_args.append("--reload")
    subprocess.run(uvicorn_args, cwd=str(ROOT), check=True)


def main():
    parser = argparse.ArgumentParser(description="AI Incident Commander")
    parser.add_argument("--setup", action="store_true", help="Install dependencies")
    parser.add_argument("--test", action="store_true", help="Run regression tests")
    parser.add_argument("--check", action="store_true", help="Check environment")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload")
    parser.set_defaults(reload=True)

    args = parser.parse_args()

    if args.setup:
        cmd_install()
    elif args.test:
        cmd_test()
    elif args.check:
        cmd_check()
    else:
        cmd_serve(args)


if __name__ == "__main__":
    main()
