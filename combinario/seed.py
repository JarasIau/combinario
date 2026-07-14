import asyncio
import logging
from typing import TypedDict

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from core.db.repositories.item import ItemRepository
from core.db.exceptions import ItemDoesNotExistError
from core.db.settings import db_settings
from schemas.item import ItemSchema

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseElement(TypedDict):
    id: int
    emoji: str
    text: str


BASE_ELEMENTS: list[BaseElement] = [
    {"id": 1, "emoji": "💧", "text": "Water"},
    {"id": 2, "emoji": "🔥", "text": "Fire"},
    {"id": 3, "emoji": "🌍", "text": "Earth"},
    {"id": 4, "emoji": "🌬️", "text": "Wind"},
]


async def prepopulate() -> None:
    logger.info("Prepopulating database with default elements.")

    engine = create_async_engine(str(db_settings.db_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = ItemRepository(session)
            for element in BASE_ELEMENTS:
                try:
                    await repository.get_item(element["id"])
                    logger.info(f"Item {element['id']} already present, skipping")
                except ItemDoesNotExistError:
                    item = ItemSchema(
                        id=element["id"],
                        emoji=element["emoji"],
                        text=element["text"],
                        parents=[],
                    )
                    item_id = await repository.add_item(
                        emoji=item.emoji, text=item.text, parents=[]
                    )
                    logger.info(f"Prepopulated with item {item_id}")

    finally:
        await engine.dispose()

    logger.info("Finished")


if __name__ == "__main__":
    asyncio.run(prepopulate())
