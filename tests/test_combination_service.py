from types import SimpleNamespace

import pytest

from core.db.exceptions import ItemDoesNotExistError
from schemas.combination import CombinationStatus
from services.combinations import CombinationService


def item(item_id: int, emoji: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=item_id, emoji=emoji, text=text, parents=[])


class FakeJob:
    job_id = "job-123"


class FakeArqPool:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def enqueue_job(self, *args: object) -> FakeJob:
        self.calls.append(args)
        return FakeJob()


class FakeRepository:
    def __init__(
        self,
        existing_combination: SimpleNamespace | None = None,
        items: dict[int, SimpleNamespace] | None = None,
    ) -> None:
        self.existing_combination = existing_combination
        self.items = items or {}
        self.parent_calls: list[tuple[int, int]] = []
        self.item_calls: list[int] = []

    async def get_item_by_parents(
        self, first_id: int, second_id: int
    ) -> SimpleNamespace:
        self.parent_calls.append((first_id, second_id))
        if self.existing_combination is None:
            raise ItemDoesNotExistError("Combination does not exist")
        return self.existing_combination

    async def get_item(self, item_id: int) -> SimpleNamespace:
        self.item_calls.append(item_id)
        try:
            return self.items[item_id]
        except KeyError:
            raise ItemDoesNotExistError("Item does not exist")


@pytest.mark.asyncio
async def test_combine_returns_existing_combination_without_enqueue() -> None:
    repository = FakeRepository(existing_combination=item(3, "💨", "Steam"))
    arq_pool = FakeArqPool()
    service = CombinationService(repository=repository, arq_pool=arq_pool)  # type: ignore[arg-type]

    result = await service.combine(1, 2)

    assert result.status == CombinationStatus.READY
    assert result.item is not None
    assert result.item.text == "Steam"
    assert arq_pool.calls == []


@pytest.mark.asyncio
async def test_combine_enqueues_missing_combination_with_normalized_pair() -> None:
    repository = FakeRepository(
        items={
            1: item(1, "💧", "Water"),
            2: item(2, "🔥", "Fire"),
        }
    )
    arq_pool = FakeArqPool()
    service = CombinationService(repository=repository, arq_pool=arq_pool)  # type: ignore[arg-type]

    result = await service.combine(2, 1)

    assert result.status == CombinationStatus.PENDING
    assert result.job_id == "job-123"
    assert repository.parent_calls == [(1, 2)]
    assert repository.item_calls == [1, 2]
    assert arq_pool.calls == [("generate_task", "Water + Fire", 1, 2)]


@pytest.mark.asyncio
async def test_combine_raises_when_source_item_is_missing() -> None:
    repository = FakeRepository(items={1: item(1, "💧", "Water")})
    service = CombinationService(repository=repository, arq_pool=FakeArqPool())  # type: ignore[arg-type]

    with pytest.raises(ItemDoesNotExistError):
        await service.combine(1, 2)
