from fastapi import FastAPI

from app.config import settings
from app.routers import auth, links, redirect

app = FastAPI(title=settings.app_name)
app.include_router(auth.router)
app.include_router(links.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(redirect.router)
