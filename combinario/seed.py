import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from core.db.repositories.item import ItemRepository
from core.db.exceptions import ItemDoesNotExistError
from core.db.settings import db_settings

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


BASE_ELEMENTS = [
    (1, "💧", "Water"),
    (2, "🔥", "Fire"),
    (3, "🌍", "Earth"),
    (4, "🌬️", "Wind"),
]


async def prepopulate() -> None:
    logger.info("Prepopulating database with default elements.")

    engine = create_async_engine(str(db_settings.db_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = ItemRepository(session)
            for item_id, emoji, text in BASE_ELEMENTS:
                try:
                    await repository.get_item(item_id)
                    logger.info(f"Item {item_id} already present, skipping")
                except ItemDoesNotExistError:
                    new_item_id = await repository.add_item(
                        emoji=emoji, text=text, parents=[]
                    )
                    logger.info(f"Prepopulated with item {new_item_id}")

    finally:
        await engine.dispose()

    logger.info("Finished")


if __name__ == "__main__":
    asyncio.run(prepopulate())
