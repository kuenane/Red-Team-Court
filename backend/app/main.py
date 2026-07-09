import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import documents, runs

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RedTeam Court API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(runs.router)


@app.get("/health")
def health():
    return {"status": "ok"}
