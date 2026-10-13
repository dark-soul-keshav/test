
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


def normalize_key(key):
    key = key.strip().lower()
    if key == "num_workers":
        return "workers"
    return key


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {
        "true", "1", "yes", "on"
    }


def convert_value(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)


def build_config(overrides):
    config = DEFAULTS.copy()

    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as f:
            config.update(yaml.safe_load(f) or {})

    for key, value in dotenv_values(".env").items():
        if key and value is not None:
            if key.startswith("APP_"):
                config[normalize_key(key[4:])] = value
            elif key == "NUM_WORKERS":
                config["workers"] = value

    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config[normalize_key(key[4:])] = value

    for item in overrides:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        config[normalize_key(key)] = value

    result = {}
    for key, value in config.items():
        result[key] = convert_value(key, value)

    result["api_key"] = "*****"
    return result


@app.get("/")
@app.get("/effective-config")
def get_effective_config(
    set_: list[str] = Query(default=[], alias="set"),
):
    return build_config(set_)
