"""Serialization contracts for domain entities."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar, get_args, get_origin, get_type_hints


DomainEntity = TypeVar("DomainEntity")


def serialize_entity(entity: Any) -> dict[str, Any]:
    if not is_dataclass(entity):
        raise TypeError("serialize_entity expects a dataclass instance")
    return {field.name: _serialize_value(getattr(entity, field.name)) for field in fields(entity)}


def deserialize_entity(model_type: type[DomainEntity], payload: dict[str, Any]) -> DomainEntity:
    type_hints = get_type_hints(model_type)
    values = {name: _deserialize_value(type_hints[name], payload[name]) for name in type_hints if name in payload}
    return model_type(**values)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _deserialize_value(expected_type: Any, value: Any) -> Any:
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if expected_type is Any:
        return value
    if origin is None:
        if isinstance(expected_type, type) and issubclass(expected_type, Enum):
            return expected_type(value)
        if expected_type is datetime:
            return datetime.fromisoformat(value)
        return value
    if origin is tuple:
        item_type = args[0] if args else Any
        return tuple(_deserialize_value(item_type, item) for item in value)
    if origin is list:
        item_type = args[0] if args else Any
        return [_deserialize_value(item_type, item) for item in value]
    if origin is dict:
        value_type = args[1] if len(args) > 1 else Any
        return {key: _deserialize_value(value_type, item) for key, item in value.items()}
    if origin is type(None):
        return None
    if origin in (set, frozenset):
        item_type = args[0] if args else Any
        return origin(_deserialize_value(item_type, item) for item in value)
    if origin is not None and type(None) in args:
        non_none = next(arg for arg in args if arg is not type(None))
        return None if value is None else _deserialize_value(non_none, value)
    return value
