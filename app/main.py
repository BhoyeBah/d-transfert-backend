from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers

app = FastAPI(title="D-Transfert API", version="0.1.0")

register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
