from pydantic import BaseModel, ConfigDict, Field


class ParentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first: int = Field(..., ge=0)
    second: int = Field(..., ge=0)

    item_id: int | None = Field(default=None, ge=0)


class ItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = Field(default=None, ge=0)
    emoji: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)

    parents: list[ParentSchema] = []


class JobSchema(BaseModel):
    enqueued: str = Field(..., min_length=1)
