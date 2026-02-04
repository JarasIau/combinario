import os
import logging
from dbmanager.dbmanager import DBManager
from dbmanager.schemas import ItemSchema

logger = logging.getLogger(__name__)

BASE_ELEMENTS = [
    {"id": 1, "emoji": "💧", "text": "Water"},
    {"id": 2, "emoji": "🔥", "text": "Fire"},
    {"id": 3, "emoji": "🌍", "text": "Earth"},
    {"id": 4, "emoji": "🌬️", "text": "Wind"},
]


def prepopulate() -> None:
    db_path = os.getenv("DB_URL")
    if not db_path:
        logger.error("Could not find DB_URL in env")
        raise ValueError
    logger.info(f"Prepopulating {db_path} with default elements.")

    dbm = DBManager(db_path=db_path)
    for element in BASE_ELEMENTS:
        if not dbm.query_item(element["id"]):
            item = ItemSchema(
                id=element["id"],
                emoji=element["emoji"],
                text=element["text"],
                parents=[],
            )
            item_id = dbm.add_item(item)
            logger.info(f"Prepopulated {db_path} with item {item_id}")
        else:
            logger.info(f"Item {element['id']} already present in {db_path}")
    dbm.close()
    logger.info("Finished")


if __name__ == "__main__":
    prepopulate()
