"""Filter builder. NEVER emits >= or <=; use => and =<."""
from __future__ import annotations

from typing import Any

ALLOWED_TYPES = {"=", "!=", "<", ">", "=<", "=>", "in", "not_in", "(.)", "[.]", "contains",
                 "is_null", "is_not_null"}
NO_VALUE = {"is_null", "is_not_null"}


class FilterError(ValueError):
    pass


def condition(field: str, type: str, value: Any = None) -> dict:
    if type in (">=", "<="):
        raise FilterError(f"operator {type!r} is forbidden; use '=>' / '=<'")
    if type not in ALLOWED_TYPES:
        raise FilterError(f"unknown filter type {type!r}")
    if not field:
        raise FilterError("field required")
    if type in ("in", "not_in") and not isinstance(value, (list, tuple)):
        raise FilterError(f"{type} needs a list value")
    c: dict[str, Any] = {"field": field, "type": type}
    if type not in NO_VALUE:
        c["value"] = list(value) if isinstance(value, tuple) else value
    return c


def build_filter(op: str, conditions: list) -> dict:
    """conditions: dicts {field,type,value}, (field,type,value) tuples, or nested group dicts {op,conditions}."""
    if op not in ("and", "or"):
        raise FilterError(f"op must be and|or, got {op!r}")
    out = []
    for c in conditions:
        if isinstance(c, dict) and "conditions" in c:
            out.append(build_filter(c.get("op", "and"), c["conditions"]))
        elif isinstance(c, dict):
            out.append(condition(c.get("field", ""), c.get("type", ""), c.get("value")))
        else:
            out.append(condition(*c))
    return {"op": op, "conditions": out}
