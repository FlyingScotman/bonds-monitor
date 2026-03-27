"""Config loading and access."""
import yaml
from pathlib import Path


_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config(path: Path | str | None = None) -> dict:
    p = Path(path) if path else _DEFAULT_CONFIG_PATH
    with open(p) as f:
        return yaml.safe_load(f)
