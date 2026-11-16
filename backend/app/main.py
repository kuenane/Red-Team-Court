import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models  # noqa: F401  (registers tables on Base.metadata)
from .config import settings
from .database import Base, engine
from .routers import documents, runs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db(attempts: int = 10, delay: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception:  # noqa: BLE001
            logger.warning("database not ready (attempt %s/%s)", attempt, attempts)
            if attempt == attempts:
                raise
            time.sleep(delay)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="RedTeam Court API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(runs.router)


@app.get("/health")
def health():
    return {"status": "ok"}
