from pydantic import BaseModel, ConfigDict, Field
from schemas.parent import ParentSchema


class ItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = Field(default=None, ge=0)
    emoji: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    parents: list[ParentSchema] = Field(default_factory=list)
