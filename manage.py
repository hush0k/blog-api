#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key.startswith("BLOG_"):
            continue
        os.environ.setdefault(key, value)


def main():
    """Run administrative tasks."""
    base_dir = Path(__file__).resolve().parent
    env_path = base_dir / "settings" / ".env"
    load_env_file(env_path)

    env_id = os.environ.get("BLOG_ENV_ID", "local").strip().lower()
    if env_id not in {"local", "prod"}:
        env_id = "local"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{env_id}")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
