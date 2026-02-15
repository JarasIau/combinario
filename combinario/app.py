import logging
import orjson
from arq import create_pool
from arq.jobs import Job, JobStatus
from arq.connections import RedisSettings, ArqRedis
from typing import Union, AsyncGenerator, cast, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dbmanager.dbmanager import DBManager
from dbmanager.schemas import ItemSchema, ParentSchema, JobSchema
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.dbm = DBManager(db_path=settings.db_url, debug=settings.debug_mode)

    redis_conn = RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
    )
    app.state.arq_pool: ArqRedis = await create_pool(redis_conn)  # type: ignore
    try:
        yield
    finally:
        await app.state.arq_pool.close()
        app.state.dbm.close()


app = FastAPI(
    lifespan=lifespan,
    json_loads=orjson.loads,
    default_response_class=ORJSONResponse,
    debug=settings.debug_mode,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


def get_dbm(request: Request) -> DBManager:
    return cast(DBManager, request.app.state.dbm)


def get_arq(request: Request) -> ArqRedis:
    return cast(ArqRedis, request.app.state.arq_pool)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/items/{first}/{second}", response_model=Union[ItemSchema, JobSchema])
async def fetch_item(
    first: int,
    second: int,
    dbm: DBManager = Depends(get_dbm),
    arq_pool: ArqRedis = Depends(get_arq),
) -> Union[ItemSchema, JobSchema]:
    if first < 1 or second < 1:
        raise HTTPException(status_code=422, detail="ID cannot be less than 1")

    parent = ParentSchema(first=first, second=second)
    item_resp = dbm.query_by_parents(parent)
    if item_resp:
        return item_resp
    first_parent = dbm.query_item(first)
    second_parent = dbm.query_item(second)
    if not first_parent or not second_parent:
        raise HTTPException(status_code=404, detail="Item not found!")
    prompt = f"{first_parent.text} + {second_parent.text}"
    job = await arq_pool.enqueue_job("generate_task", prompt, first, second)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to enqueue a job")
    return JobSchema(enqueued=job.job_id)


@app.get("/task/{job_id}")
async def fetch_task(
    job_id: str, arq_pool: ArqRedis = Depends(get_arq)
) -> dict[str, Any]:
    job = Job(job_id=job_id, redis=arq_pool)
    status = await job.status()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found!")
    if status == JobStatus.complete:
        try:
            return {"status": "complete", "result": await job.result()}
        except Exception as e:
            logger.error(e)
            return {"status": "failed"}
    return {"status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
