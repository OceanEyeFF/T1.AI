"""模型层：抽象基类 + 注册表 + 模型实现。"""

from .base import ModelABC, PredictionData, PredictionResult, TrainingData, TrainingResult
from .registry import (
    create_model as _create_model,
    create_model_from_toml as _create_model_from_toml,
    get_model_class as _get_model_class,
    list_registered_models as _list_registered_models,
    register_model,
)

# 自动发现
_imported = False


def _ensure_models_imported() -> None:
    global _imported
    if _imported:
        return
    from pathlib import Path

    models_dir = Path(__file__).parent
    for sub_dir in sorted(models_dir.iterdir()):
        if sub_dir.is_dir() and (sub_dir / "__init__.py").exists():
            name = sub_dir.name
            if name.startswith("_") or name == "__pycache__":
                continue
            try:
                __import__(f"ashare_lab.models.{name}", fromlist=["__all__"])
            except Exception:
                pass
    _imported = True


def create_model(name: str, **config):
    _ensure_models_imported()
    return _create_model(name, **config)


def create_model_from_toml(toml_path, **overrides):
    _ensure_models_imported()
    return _create_model_from_toml(toml_path, **overrides)


def get_model_class(name: str):
    _ensure_models_imported()
    return _get_model_class(name)


def list_registered_models():
    _ensure_models_imported()
    return _list_registered_models()


__all__ = [
    "ModelABC",
    "PredictionData",
    "PredictionResult",
    "TrainingData",
    "TrainingResult",
    "create_model",
    "create_model_from_toml",
    "get_model_class",
    "list_registered_models",
    "register_model",
]
