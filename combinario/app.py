import os
import logging
import orjson
from arq import create_pool
from arq.jobs import Job, JobStatus
from arq.connections import RedisSettings, ArqRedis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dbmanager.dbmanager import DBManager
from dbmanager.schemas import ItemSchema, ParentSchema


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.dbm = DBManager(db_path=os.getenv("DB_PATH"))

    redis_conn = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
    app.state.arq_pool: ArqRedis = await create_pool(connection=redis_conn)
    yield
    await app.state.arq_pool.close()
    app.state.dbm.close()


app = FastAPI(
    lifespan=lifespan,
    json_loads=orjson.loads,
    default_response_class=ORJSONResponse,
    debug=False,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s: %(message)s")
logger.setLevel(logging.INFO)


def get_dbm(request: Request) -> DBManager:
    return request.app.state.dbm


def get_arq(request: Request) -> ArqRedis:
    return request.app.state.arq_pool


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/items/{first}/{second}", response_model=ItemSchema)
def fetch_item(
    first: int,
    second: int,
    dbm: DBManager = Depends(get_dbm),
    arq_pool: ArqRedis = Depends(get_arq),
):
    parent = ParentSchema(first=first, second=second)
    item_resp = dbm.query_by_parents(parent)
    if item_resp:
        return ItemSchema.model_validate(item_resp)
    first_parent = dbm.query_item(first)
    second_parent = dbm.query_item(second)
    prompt = f"{first_parent.text} + {second_parent.text}"
    job = await arq_pool.enqueue("generate_task", prompt)
    return {"enqueued": job.id}


@app.get("/task/{job_id}")
async def fetch_task(job_id: str, arq_pool: ArqRedis = Depends(get_arq)):
    job = Job(job_id, arq_pool)
    status = await job.status()
    if not job or status == JobStatus.not_found:
        raise HTTPException(status_code=404, detail="Job not found!")
    if status == JobStatus.complete:
        return {"status": status, "result": await job.result()}
    return {"status": status}
