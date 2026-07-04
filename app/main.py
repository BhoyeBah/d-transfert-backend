from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.routers import auth, companies, employees

app = FastAPI(title="D-Transfert API", version="0.1.0")

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(employees.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
