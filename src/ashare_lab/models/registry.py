"""模型注册表。

提供按配置创建模型实例、模型发现、版本管理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Type

from .base import ModelABC

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


_MODEL_REGISTRY: dict[str, Type[ModelABC]] = {}


def register_model(name: str, cls: Type[ModelABC]) -> None:
    """注册模型类。

    Args:
        name: 模型名称（与 cls.name 一致）
        cls: 模型类
    """
    _MODEL_REGISTRY[name] = cls


def get_model_class(name: str) -> Type[ModelABC]:
    """获取已注册的模型类。

    Raises:
        KeyError: 未注册
    """
    if name not in _MODEL_REGISTRY:
        raise KeyError(f"model '{name}' not registered. Available: {list(_MODEL_REGISTRY.keys())}")
    return _MODEL_REGISTRY[name]


def create_model(name: str, **config: Any) -> ModelABC:
    """按配置创建模型实例。

    Args:
        name: 注册的模型名称
        **config: 传递给模型 __init__ 的参数

    Returns:
        模型实例
    """
    cls = get_model_class(name)
    return cls(**config)


def create_model_from_toml(toml_path: str | Path, **overrides: Any) -> ModelABC:
    """从 TOML 配置文件创建模型实例。

    TOML 格式：
        [model]
        name = "transformer"
        input_dim = 6
        d_model = 128
        ...

    Args:
        toml_path: TOML 配置文件路径
        **overrides: 覆盖 TOML 中的字段

    Returns:
        模型实例
    """
    payload = tomllib.loads(Path(toml_path).read_text(encoding="utf-8"))

    model_section = payload.get("model", {})
    if not isinstance(model_section, dict):
        raise ValueError(f"TOML must contain a [model] section: {toml_path}")

    model_name = str(model_section.pop("name", ""))
    if not model_name:
        raise ValueError(f"[model] section must contain 'name' field: {toml_path}")

    # 合并 TOML 参数与 overrides
    config = {**model_section, **overrides}
    return create_model(model_name, **config)


def list_registered_models() -> list[str]:
    """列出所有已注册的模型名称。"""
    return sorted(_MODEL_REGISTRY.keys())
