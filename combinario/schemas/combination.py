from enum import Enum

from pydantic import BaseModel, Field, model_validator

from schemas.item import ItemSchema


class CombinationStatus(str, Enum):
    READY = "ready"
    PENDING = "pending"


class CombinationRequest(BaseModel):
    first_id: int = Field(..., ge=1)
    second_id: int = Field(..., ge=1)


class CombinationResponse(BaseModel):
    status: CombinationStatus
    item: ItemSchema | None = None
    job_id: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "CombinationResponse":
        if self.status == CombinationStatus.READY and self.item is None:
            raise ValueError("ready combinations require an item")
        if self.status == CombinationStatus.PENDING and self.job_id is None:
            raise ValueError("pending combinations require a job_id")
        return self
