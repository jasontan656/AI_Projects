from __future__ import annotations
from shared_utilities.time import Time

from datetime import timedelta
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


def _default_expiry(minutes: int = 10) -> "datetime":
    return Time.now_plus(timedelta(minutes=minutes))


class FormSubmissionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str = Field(..., description="UUID generated per render")
    expires_at: "datetime" = Field(default_factory=_default_expiry)
    step_id: str
    errors: Dict[str, str] = Field(default_factory=dict)


__all__ = ["FormSubmissionContract"]

