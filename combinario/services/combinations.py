from typing import Any

from core.db.exceptions import ItemDoesNotExistError
from schemas.combination import CombinationResponse, CombinationStatus
from schemas.item import ItemSchema
from schemas.parent import ParentSchema


class CombinationService:
    def __init__(self, repository: Any, arq_pool: Any):
        self.repository = repository
        self.arq_pool = arq_pool

    async def combine(self, first_id: int, second_id: int) -> CombinationResponse:
        parent = ParentSchema(first=first_id, second=second_id)

        try:
            item = await self.repository.get_item_by_parents(
                first_id=parent.first, second_id=parent.second
            )
            return CombinationResponse(
                status=CombinationStatus.READY,
                item=ItemSchema.model_validate(item),
            )
        except ItemDoesNotExistError:
            pass

        try:
            first_item = ItemSchema.model_validate(
                await self.repository.get_item(parent.first)
            )
            second_item = ItemSchema.model_validate(
                await self.repository.get_item(parent.second)
            )
        except ItemDoesNotExistError:
            raise

        prompt = f"{first_item.text} + {second_item.text}"
        job = await self.arq_pool.enqueue_job(
            "generate_task", prompt, parent.first, parent.second
        )
        if job is None:
            raise RuntimeError("Failed to enqueue generation job")

        return CombinationResponse(
            status=CombinationStatus.PENDING,
            job_id=job.job_id,
        )

    async def get_existing(self, first_id: int, second_id: int) -> ItemSchema:
        parent = ParentSchema(first=first_id, second=second_id)
        item = await self.repository.get_item_by_parents(
            first_id=parent.first, second_id=parent.second
        )
        return ItemSchema.model_validate(item)
