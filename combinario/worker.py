import os
import logging
from arq.connections import RedisSettings
from dbmanager.dbmanager import DBManager
from dbmanager.schemas import ItemSchema, ParentSchema
from models.model import OpenAI

logger = logging.getLogger(__name__)


async def generate_task(ctx: dict, prompt: str, first: int, second: int) -> ItemSchema:
    openai_client = ctx["openai_client"]
    dbm = ctx["dbm"]
    logger.info(f"Generating {prompt}")
    result = await openai_client.generate(prompt)
    try:
        emoji, text = result.split(maxsplit=1)
    except ValueError:
        emoji = result[0]
        text = result[1:]
    item = ItemSchema(
        emoji=emoji, text=text, parents=[ParentSchema(first=first, second=second)]
    )
    item.id = dbm.add_item(item)
    return item


async def startup(ctx: dict) -> None:
    ctx["openai_client"] = OpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "EMPTY"),
        max_tokens=int(os.getenv("MAX_TOKENS", 20)),
        temperature=float(os.getenv("MODEL_TEMPERATURE", 0.7)),
    )
    ctx["dbm"] = DBManager(db_path=os.getenv("DB_URL", "sqlite:///:memory:"))
    logging.info("ARQ worker created")


async def shutdown(ctx: dict) -> None:
    dbm = ctx.get("dbm")
    if dbm:
        dbm.close()
    logger.info("ARQ worker shutdown")


class WorkerSettings:
    functions = [generate_task]
    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
