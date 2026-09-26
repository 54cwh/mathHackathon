"""运行日志（core §0）。

structlog 输出 **JSONL**，字段对齐 **OpenTelemetry Logs Data Model**：
``timestamp``（ISO-8601 UTC）、``severity_number`` / ``severity_text``、``event``（Body）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TextIO

import structlog

# OpenTelemetry Logs SeverityNumber（Stable）常用档位
SEVERITY_NUMBERS: dict[str, int] = {
    "debug": 5,
    "info": 9,
    "warning": 13,
    "error": 17,
    "critical": 21,
}

_LEVELS: dict[str, int] = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}

_handle: TextIO | None = None


def _add_otel_severity(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    level = event_dict.pop("level", method_name or "info")
    event_dict["severity_number"] = SEVERITY_NUMBERS.get(level, 9)
    event_dict["severity_text"] = level.upper()
    return event_dict


def configure_logging(
    log_path: str | Path | None = None,
    *,
    level: str = "info",
    resource: dict[str, Any] | None = None,
) -> None:
    """配置全局 structlog。

    ``log_path`` 给出时写 JSONL 到该文件（UTF-8、每行一个对象）；否则写 stderr。
    ``resource`` 作为公共字段（如 ``experiment_id``）绑定到每条日志。
    """
    global _handle
    if level not in _LEVELS:
        raise ValueError(f"未知日志级别：{level!r}")
    if _handle is not None:
        _handle.close()
        _handle = None

    if resource:
        structlog.contextvars.bind_contextvars(**resource)

    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _handle = path.open("a", encoding="utf-8", buffering=1)
        factory: Any = structlog.WriteLoggerFactory(file=_handle)
    else:
        factory = structlog.PrintLoggerFactory(file=sys.stderr)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _add_otel_severity,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=factory,
        wrapper_class=structlog.make_filtering_bound_logger(_LEVELS[level]),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)
