from pathlib import Path
import subprocess
import sys


BACKEND_ROOT = Path(__file__).resolve().parent
ENV_FILE = BACKEND_ROOT / ".env"


def _read_env_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix):].strip()
        if value.startswith(("\"", "'")) and value.endswith(("\"", "'")) and len(value) >= 2:
            value = value[1:-1]
        return value
    return None


def _warn_on_missing_env() -> None:
    if not ENV_FILE.exists():
        print(
            f"[warn] Missing {ENV_FILE.name} in {BACKEND_ROOT}. "
            "Copy .env.example to .env and fill in SMTP_HOST, SMTP_USER, SMTP_PASS, and SMTP_FROM if needed."
        )
        return

    try:
        env_text = ENV_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[warn] Could not read {ENV_FILE}: {exc}")
        return

    missing = [
        key
        for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS")
        if not _read_env_value(env_text, key)
    ]
    if missing:
        print(
            f"[warn] {ENV_FILE.name} is present but missing: {', '.join(missing)}. "
            "Auth OTP email delivery will fail until these are set."
        )

services = [
    ("gateway", 8000),
    ("auth", 8001),
    ("catalog", 8002),
    ("orders", 8003),
    ("analytics", 8004),
    ("audit", 8005),
    ("genai", 8006),
]

processes = []

_warn_on_missing_env()

for name, port in services:
    print(f"Starting {name} on port {port}")

    p = subprocess.Popen([
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
        "--reload"
    ], cwd=name)

    processes.append(p)

try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("Stopping all services...")
    for p in processes:
        p.terminate()