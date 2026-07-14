import logging
import orjson
from http import HTTPStatus
from arq import create_pool
from arq.jobs import Job, JobStatus
from arq.connections import RedisSettings, ArqRedis
from typing import AsyncGenerator, Union, Any
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from schemas.item import ItemSchema
from schemas.parent import ParentSchema
from schemas.job import JobSchema

from core.redis.dependencies import RedisDep
from core.db.dependencies import ItemRepoDep
from core.db.exceptions import ItemDoesNotExistError

from core.db.settings import db_settings
from core.redis.settings import redis_settings


logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    engine = create_async_engine(str(db_settings.db_url), echo=db_settings.debug_mode)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield
    finally:
        await engine.dispose()


@asynccontextmanager
async def redis_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    redis_conn = RedisSettings(
        host=redis_settings.redis_host, port=redis_settings.redis_port
    )
    app.state.arq_pool: ArqRedis = await create_pool(redis_conn)  # type: ignore
    try:
        yield
    finally:
        await app.state.arq_pool.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with AsyncExitStack() as stack:
        for ls in [db_lifespan, redis_lifespan]:
            await stack.enter_async_context(ls(app))
        yield


app = FastAPI(
    lifespan=lifespan,
    json_loads=orjson.loads,
    default_response_class=ORJSONResponse,
    debug=db_settings.debug_mode,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/items/{first}/{second}", response_model=Union[ItemSchema, JobSchema])
async def fetch_item(
    first: int,
    second: int,
    repository: ItemRepoDep,
    arq_pool: RedisDep,
) -> Union[ItemSchema, JobSchema]:
    if first < 1 or second < 1:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="IDs must be >= 1"
        )

    parent = ParentSchema(first=first, second=second)
    try:
        return ItemSchema.model_validate(
            await repository.get_item_by_parents(
                first_id=parent.first, second_id=parent.second
            )
        )
    except ItemDoesNotExistError:
        try:
            first_item = ItemSchema.model_validate(await repository.get_item(first))
            second_item = ItemSchema.model_validate(await repository.get_item(second))
        except ItemDoesNotExistError:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="Item not found"
            )

    prompt = f"{first_item.text} + {second_item.text}"
    job = await arq_pool.enqueue_job("generate_task", prompt, first, second)
    if not job:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to enqueue job"
        )
    return JobSchema(enqueued=job.job_id)


@app.get("/task/{job_id}")
async def fetch_task(job_id: str, arq_pool: RedisDep) -> dict[str, Any]:
    job = Job(job_id=job_id, redis=arq_pool)
    status = await job.status()

    if status == JobStatus.not_found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found")

    if status == JobStatus.complete:
        try:
            return {"status": "complete", "result": await job.result()}
        except Exception as e:
            logger.error("Failed to retrieve result for job %s: %s", job_id, e)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Job failed"
            )

    return {"status": status.value}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
