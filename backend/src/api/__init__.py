from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="MegaLoja Online API",
    description="Fornece as principais funções do e-commerce MegaLoja online.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

from .routes import orders, products, stores

app.include_router(products.router)
app.include_router(stores.router)
app.include_router(orders.router)

DOCS = Path(__file__).resolve().parents[3] / "docs"
if DOCS.is_dir():
    app.mount("/app", StaticFiles(directory=DOCS, html=True), name="front")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(DOCS / "index.html")

    @app.get("/config.js", include_in_schema=False)
    def config():
        return FileResponse(DOCS / "config.js")


def main() -> None:
    uvicorn.run("api:app", host="127.0.0.1", port=8000)
