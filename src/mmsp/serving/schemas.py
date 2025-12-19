"""Request/response schemas for gateway."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    entity_id: str = Field(..., description="Entity identifier used for feature lookup")
    features: Optional[Dict[str, float]] = Field(
        default=None, description="Optional features; otherwise pulled from store"
    )


class PredictResponse(BaseModel):
    prediction: float
    model_name: str
    model_version: int
    phase: str
    latency_ms: float
    features: Dict[str, float]
