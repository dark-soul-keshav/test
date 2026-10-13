
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def convert(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return as_bool(value)
    return str(value)


def effective_config(overrides):
    config = DEFAULTS.copy()

    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as f:
            config.update(yaml.safe_load(f) or {})

    env_file = dotenv_values(".env")
    for key, value in env_file.items():
        if key and key.startswith("APP_") and value is not None:
            config[key[4:].lower()] = value

    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config[key[4:].lower()] = value

    for item in overrides:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        config[key] = value

    result = {}
    for key, value in config.items():
        result[key] = convert(key, value)

    result["api_key"] = "*****"
    return result


@app.get("/effective-config")
@app.get("/effective-configs")
def get_effective_config(
    set: list[str] = Query(default=[]),
):
    return effective_config(set)
