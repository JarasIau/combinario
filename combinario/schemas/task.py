from pydantic import BaseModel

from schemas.item import ItemSchema


class TaskResponse(BaseModel):
    status: str
    item: ItemSchema | None = None
