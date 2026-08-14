"""Test helper: serialize a nested mapping as TOML text (config fixture 用途)。

项目配置已统一为真 TOML（D1）；测试内生成临时 config 时用本助手，
不再写 YAML/JSON 伪配置。
"""

from __future__ import annotations

import json
from typing import Any


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    raise TypeError(f"unsupported TOML value: {v!r}")


def dump_mapping_toml(cfg: dict[str, Any]) -> str:
    """递归把嵌套 dict 渲染为 TOML 文本（表头 + 标量键）。"""
    lines: list[str] = []

    def walk(d: dict[str, Any], prefix: str) -> None:
        for k, v in d.items():
            if isinstance(v, dict):
                header = f"{prefix}{k}" if prefix else str(k)
                lines.append(f"[{header}]")
                walk(v, f"{header}.")
            else:
                lines.append(f"{k} = {_toml_value(v)}")

    walk(cfg, "")
    return "\n".join(lines) + "\n"
