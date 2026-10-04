from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Tuple


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    if isinstance(value, frozenset):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class PostSpec:
    """Validated content boundary shared by renderers and caption generation."""
    kind: str
    date: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    illustrative: bool = False
    warnings: Tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "facts", _freeze(dict(self.facts)))
        object.__setattr__(self, "warnings", tuple(self.warnings))

    def to_dict(self):
        return {"kind": self.kind, "date": self.date, "facts": _thaw(self.facts),
                "illustrative": self.illustrative, "warnings": list(self.warnings)}
