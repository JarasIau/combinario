import os
import logging
import orjson
from dbmanager.dbmanager import DBManager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


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

dbm: DBManager = None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/task/{task_id}")
async def fetch_task(task_id: int):
    pass


@app.get("/items/{first}/{second}")
def fetch_item(first: int, second: int):
    item = dbm.query(first=first, second=second)
    if item:
        return {"id": item.id, "emoji": item.emoji, "text": item.text}
    """delegate to vllm"""


@app.on_event("startup")
async def startup():
    global dbm

    db_path = os.getenv("DB_PATH")
    dbm = DBManager(db_path=db_path)

    """vllm init"""
    """redis init"""


@app.on_event("shutdown")
async def shutdown():
    dbm.close()
