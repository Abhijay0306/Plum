from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str


class TraceEvent(BaseModel):
    step: int
    agent: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str  # SUCCESS | FAILED | SKIPPED | WARNING
    input_summary: str
    output_summary: str
    checks: list[CheckResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    confidence_delta: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceLog(BaseModel):
    claim_id: str
    events: list[TraceEvent] = Field(default_factory=list)
    degraded_components: list[str] = Field(default_factory=list)
    base_confidence: float = 1.0

    def add_event(self, event: TraceEvent) -> None:
        event.step = len(self.events) + 1
        self.events.append(event)

    def mark_degraded(self, component: str) -> None:
        if component not in self.degraded_components:
            self.degraded_components.append(component)

    @property
    def final_confidence(self) -> float:
        delta = sum(e.confidence_delta for e in self.events)
        return max(0.0, min(1.0, self.base_confidence + delta))
