"""Memento pattern: snapshots of the calculator history for undo/redo."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from app.calculation import Calculation


@dataclass
class CalculatorMemento:
    """An immutable snapshot of the calculation history at a point in time."""

    history: List[Calculation]
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # Copy the list so later changes to the calculator don't alter the snapshot.
        self.history = list(self.history)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history": [calc.to_dict() for calc in self.history],
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalculatorMemento":
        return cls(
            history=[Calculation.from_dict(item) for item in data["history"]],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
