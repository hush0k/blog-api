import os
from pathlib import Path

try:
    from decouple import AutoConfig, Csv
except Exception:
    AutoConfig = None
    Csv = None

if AutoConfig is not None:
    _CONFIG = AutoConfig(search_path=str(Path(__file__).resolve().parent))
else:
    _CONFIG = None


def env_bool(name: str, default: bool = False) -> bool:
    if _CONFIG is not None:
        return _CONFIG(name, default=default, cast=bool)
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_str(name: str, default: str | None = None) -> str | None:
    if _CONFIG is not None:
        return _CONFIG(name, default=default)
    return os.environ.get(name, default)


def env_int(name: str, default: int | None = None) -> int | None:
    if _CONFIG is not None:
        return _CONFIG(name, default=default, cast=int)
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    if default is None:
        default = []
    if _CONFIG is not None and Csv is not None:
        return _CONFIG(name, default=default, cast=Csv())
    value = os.environ.get(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]
