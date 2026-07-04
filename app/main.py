from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.routers import (
    admin,
    audit_logs,
    auth,
    clients,
    collaborations,
    companies,
    dashboard,
    employees,
    entries,
    national_operations,
    notifications,
    payments,
    private_rates,
    reports,
    suppliers,
    transfers,
    wallets,
)

app = FastAPI(
    title="D-Transfert API",
    version="0.1.0",
    description=(
        "API backend de D-Transfert : gestion multi-entreprises des wallets, opérations "
        "nationales, collaborations inter-entreprises, envois internationaux, paiements "
        "collaborateurs, clients, fournisseurs, dashboard et audit. Authentification par "
        "matricule d'entreprise (Owner) ou matricule+téléphone (Employé), JWT access/refresh. "
        "Isolation stricte par company_id dérivé du token — aucune requête ne doit référencer "
        "une entreprise autre que la sienne."
    ),
)

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
app.include_router(notifications.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
