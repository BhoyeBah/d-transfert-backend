from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.routers import (
    auth,
    clients,
    collaborations,
    companies,
    employees,
    entries,
    national_operations,
    payments,
    private_rates,
    suppliers,
    transfers,
    wallets,
)

app = FastAPI(title="D-Transfert API", version="0.1.0")

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(employees.router)
app.include_router(wallets.router)
app.include_router(national_operations.router)
app.include_router(collaborations.router)
app.include_router(private_rates.router)
app.include_router(entries.router)
app.include_router(transfers.router)
app.include_router(payments.router)
app.include_router(clients.router)
app.include_router(suppliers.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
