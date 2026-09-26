"""稳定 ID 注册表（core §0）。

语义对齐 **MLflow Model Registry**：稳定名 + 不可变版本 + 可变别名（``champion`` 等）
+ tags + 血缘 ``source_run_id``；本地 JSON 索引实现（离线）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class Registry:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.is_file():
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict) or "models" not in loaded:
                raise ValueError(f"注册表文件格式非法：{self._path}")
            return loaded
        return {"models": {}}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _model(self, name: str) -> dict[str, Any]:
        try:
            return self._data["models"][name]
        except KeyError as exc:
            raise KeyError(f"未注册的模型名：{name!r}") from exc

    def register(
        self,
        name: str,
        version: str,
        *,
        path: str | None = None,
        run_id: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        if not name or not version:
            raise ValueError("name 与 version 均不能为空")
        model = self._data["models"].setdefault(name, {"versions": {}, "aliases": {}})
        if version in model["versions"]:
            raise FileExistsError(f"{name}@{version} 已存在；版本不可变")
        entry = {
            "name": name,
            "version": version,
            "source_run_id": run_id,
            "path": path,
            "tags": dict(tags or {}),
        }
        model["versions"][version] = entry
        self._save()
        return entry

    def set_alias(self, name: str, alias: str, version: str) -> None:
        model = self._model(name)
        if version not in model["versions"]:
            raise KeyError(f"{name}@{version} 不存在")
        model["aliases"][alias] = version
        self._save()

    def resolve(self, name: str, alias: str | None = None) -> dict[str, Any]:
        model = self._model(name)
        if alias is None:
            raise ValueError("resolve 需要 alias（版本须显式指定）")
        try:
            version = model["aliases"][alias]
        except KeyError as exc:
            raise KeyError(f"{name} 无别名：{alias!r}") from exc
        return model["versions"][version]

    def versions(self, name: str) -> list[str]:
        return list(self._model(name)["versions"].keys())

    def aliases(self, name: str) -> dict[str, str]:
        return dict(self._model(name)["aliases"])

    def list_models(self) -> list[str]:
        return list(self._data["models"].keys())
