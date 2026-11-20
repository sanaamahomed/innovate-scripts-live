"""Loads qa-app/.env into the environment on import (real environment variables win).
Lets Windows / no-Docker runs use a plain .env file with no extra tools."""
import os
from pathlib import Path


def load_env(path=Path(__file__).parent / ".env"):
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v.strip():
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
