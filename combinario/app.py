import logging
import orjson
from http import HTTPStatus
from pathlib import Path
from arq import create_pool
from arq.jobs import Job, JobStatus
from arq.connections import RedisSettings, ArqRedis
from typing import AsyncGenerator, Union, Any
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from schemas.combination import (
    CombinationRequest,
    CombinationResponse,
    CombinationStatus,
)
from schemas.item import ItemSchema
from schemas.job import JobSchema
from schemas.task import TaskResponse

from core.redis.dependencies import RedisDep
from core.db.dependencies import ItemRepoDep
from core.db.exceptions import ItemDoesNotExistError
from services.combinations import CombinationService

from core.db.settings import db_settings
from core.redis.settings import redis_settings


logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


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
        host=redis_settings.redis_host,
        port=redis_settings.redis_port,
        database=redis_settings.redis_db,
        password=redis_settings.redis_password or None,
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
    docs_url="/docs" if db_settings.debug_mode else None,
    redoc_url=None,
    openapi_url="/openapi.json" if db_settings.debug_mode else None,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


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
    result = await _combine_items(first, second, repository, arq_pool)
    if result.status == CombinationStatus.READY and result.item is not None:
        return result.item
    if result.status == CombinationStatus.PENDING and result.job_id is not None:
        return JobSchema(enqueued=result.job_id)
    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="Invalid combination response",
    )


@app.post("/api/combinations", response_model=CombinationResponse)
async def create_combination(
    payload: CombinationRequest,
    response: Response,
    repository: ItemRepoDep,
    arq_pool: RedisDep,
) -> CombinationResponse:
    result = await _combine_items(
        payload.first_id, payload.second_id, repository, arq_pool
    )
    if result.status == CombinationStatus.PENDING:
        response.status_code = HTTPStatus.ACCEPTED
    return result


@app.get("/api/combinations/{first}/{second}", response_model=ItemSchema)
async def fetch_combination(
    first: int,
    second: int,
    repository: ItemRepoDep,
    arq_pool: RedisDep,
) -> ItemSchema:
    if first < 1 or second < 1:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="IDs must be >= 1"
        )

    service = CombinationService(repository=repository, arq_pool=arq_pool)
    try:
        return await service.get_existing(first, second)
    except ItemDoesNotExistError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Combination not found"
        )


async def _combine_items(
    first: int,
    second: int,
    repository: ItemRepoDep,
    arq_pool: RedisDep,
) -> CombinationResponse:
    if first < 1 or second < 1:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="IDs must be >= 1"
        )

    service = CombinationService(repository=repository, arq_pool=arq_pool)
    try:
        return await service.combine(first, second)
    except ItemDoesNotExistError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    except RuntimeError as e:
        logger.error("Failed to enqueue generation job: %s", e)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to enqueue job"
        )


@app.get("/task/{job_id}")
async def fetch_task(job_id: str, arq_pool: RedisDep) -> dict[str, Any]:
    task = await _fetch_task(job_id, arq_pool)
    if task.status == "complete":
        return {"status": task.status, "result": task.item}
    return {"status": task.status}


@app.get("/api/jobs/{job_id}", response_model=TaskResponse)
async def fetch_job(job_id: str, arq_pool: RedisDep) -> TaskResponse:
    return await _fetch_task(job_id, arq_pool)


async def _fetch_task(job_id: str, arq_pool: RedisDep) -> TaskResponse:
    job = Job(job_id=job_id, redis=arq_pool)
    status = await job.status()

    if status == JobStatus.not_found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found")

    if status == JobStatus.complete:
        try:
            return TaskResponse(
                status="complete", item=ItemSchema.model_validate(await job.result())
            )
        except Exception as e:
            logger.error("Failed to retrieve result for job %s: %s", job_id, e)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Job failed"
            )

    return TaskResponse(status=status.value)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
