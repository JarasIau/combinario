import logging
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from schemas.item import ItemSchema
from schemas.parent import ParentSchema

from core.db.repositories.item import ItemRepository

from core.llm.model import OpenAI
from core.llm.parser import LLMOutputError, parse_llm_item

from core.db.settings import db_settings
from core.llm.settings import llm_settings
from core.redis.settings import redis_settings

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_task(
    ctx: dict[str, Any],
    prompt: str,
    first: int,
    second: int,
) -> ItemSchema:
    openai_client = ctx["openai_client"]
    session_factory = ctx["session_factory"]

    logger.info(f"Generating {prompt}")
    if not (result := await openai_client.generate(prompt)):
        raise Exception("Empty LLM response")

    try:
        generated = parse_llm_item(result)
    except LLMOutputError as e:
        raise ValueError(f"Invalid LLM response: {e}") from e

    parent = ParentSchema(first=first, second=second)
    item = ItemSchema(emoji=generated.emoji, text=generated.text, parents=[parent])

    async with session_factory() as session:
        repository = ItemRepository(session)
        item.id = await repository.add_item(
            emoji=item.emoji, text=item.text, parents=[(parent.first, parent.second)]
        )

    return item


async def startup(ctx: dict[str, Any]) -> None:
    engine = create_async_engine(str(db_settings.db_url), echo=db_settings.debug_mode)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)
    ctx["openai_client"] = OpenAI(
        model=llm_settings.llm_model,
        base_url=llm_settings.llm_base_url,
        api_key=llm_settings.open_ai_api_key,
        max_tokens=llm_settings.max_tokens,
        temperature=llm_settings.model_temperature,
    )
    logger.info("ARQ worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    if engine := ctx.get("engine"):
        await engine.dispose()
    logger.info("ARQ worker shutdown")


class WorkerSettings:
    functions = [generate_task]
    on_startup = startup
    on_shutdown = shutdown

    redis_settings = redis_settings.as_arq_settings()
