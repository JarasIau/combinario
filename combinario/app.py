import os
import logging
import orjson
from redis import Redis
from rq import Queue
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dbmanager.dbmanager import DBManager
from dbmanager.schemas import ItemSchema, ParentSchema


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.getenv("DB_PATH")
    app.state.dbm = DBManager(db_path=db_path)

    """TODO: vllm init"""
    redis_conn = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
    app.state.redis_queue = Queue(connection=redis_conn)
    yield
    app.state.redis_queue.delete(delete_jobs=True)
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


def get_rq(request: Request) -> Queue:
    return request.app.state.redis_queue


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/items/{first}/{second}", response_model=ItemSchema)
def fetch_item(
    first: int,
    second: int,
    dbm: DBManager = Depends(get_dbm),
    redis_queue: Queue = Depends(get_rq),
):
    parent = ParentSchema(first=first, second=second)
    item_resp = dbm.query(parent)
    if item_resp:
        return ItemSchema.model_validate(item_resp)
    job = redis_queue.enqueue("""TODO: delegate to vllm""")
    return {"enqueued": job.id}


@app.get("/task/{job_id}")
async def fetch_task(job_id: str, redis_queue: Queue = Depends(get_rq)):
    job = redis_queue.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found!")
    if job.is_finished:
        return {"status": job.get_status(), "result": job.result}
    return {"status": job.get_status()}
