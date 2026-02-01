import os
import logging
import orjson
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dbmanager.dbmanager import DBManager
from dbmanager.schemas import ItemSchema, ParentSchema


app = FastAPI(
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/items/{first}/{second}", response_model=ItemSchema)
def fetch_item(first: int, second: int, dbm: DBManager = Depends(get_dbm)):
    parent = ParentSchema(first=first, second=second)
    item_resp = dbm.query(parent)
    if item_resp:
        return ItemSchema.model_validate(item_resp)
    """TODO: delegate to vllm"""


@app.get("/task/{task_id}")
async def fetch_task(task_id: int):
    """TODO: fetch an ongoing job from redis"""


@app.on_event("startup")
async def startup():
    db_path = os.getenv("DB_PATH")
    app.state.dbm = DBManager(db_path=db_path)

    """TODO: vllm init"""
    """TODO: redis init"""


@app.on_event("shutdown")
async def shutdown():
    app.state.dbm.close()
