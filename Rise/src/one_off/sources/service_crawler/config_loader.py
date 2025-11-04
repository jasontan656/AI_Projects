import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
_CONFIG_CACHE = None


def load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        with CONFIG_PATH.open('r', encoding='utf-8') as fh:
            _CONFIG_CACHE = yaml.safe_load(fh) or {}
    return _CONFIG_CACHE


def resolve_path(path_key):
    config = load_config()
    paths = config.get('paths', {})
    raw = paths.get(path_key)
    if raw is None:
        raise KeyError(f"paths.{path_key} not configured")
    path = Path(raw)
    if not path.is_absolute():
        path = CONFIG_PATH.parent / path
    return path


def get_llm_config(name):
    config = load_config()
    llm = config.get('llm', {})
    if name not in llm:
        raise KeyError(f"llm.{name} not configured")
    return llm[name]


def get_site_config():
    config = load_config()
    return config.get('site', {})
