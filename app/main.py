from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import pages, actions

app = FastAPI(title="SoziCheckSG", version="0.1.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(actions.router)
