"""Aggregate metrics endpoint.

Strict privacy enforcement:
- Accepts only allowed aggregate counts.
- No user identifiers or demographics are accepted.
- Rejects any payload containing extra or log fields with HTTP 422.
"""
from __future__ import annotations

from enum import Enum
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from server.db import record_aggregate_metric

router = APIRouter(prefix="/metrics", tags=["metrics"])


class AllowedMetric(str, Enum):
    APP_OPENED_COUNT = "app_opened_count"
    FEDERATED_ROUND_COMPLETED = "federated_round_completed"
    SCREEN_VIEW_COUNT = "screen_view_count"
    ACTIVE_USERS_DAILY = "active_users_daily"
    CONTENT_CARD_OPENED = "content_card_opened"
    AUDIO_LISTENED_COUNT = "audio_listened_count"


class AggregateMetricSubmission(BaseModel):
    """Aggregate metric payload. Extra fields are strictly forbidden."""
    model_config = ConfigDict(extra="forbid")

    metric_name: AllowedMetric
    value: float = Field(..., ge=0, description="Non-negative numeric count or aggregate score")


@router.post("/aggregate", status_code=status.HTTP_201_CREATED)
def submit_aggregate_metric(payload: AggregateMetricSubmission):
    """Records an anonymized aggregate system count."""
    metric_id = record_aggregate_metric(
        metric_name=payload.metric_name.value,
        value=payload.value
    )
    return {
        "status": "recorded",
        "id": metric_id,
        "metric_name": payload.metric_name.value,
        "value": payload.value
    }
