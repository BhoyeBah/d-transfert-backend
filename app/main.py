from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# API JSON pure (jamais de rendu HTML de contenu utilisateur ici, le frontend Next.js
# porte sa propre CSP) : X-Frame-Options/X-Content-Type-Options/Referrer-Policy suffisent
# côté API. HSTS uniquement en production pour ne pas piéger un accès direct en HTTP en
# développement (le navigateur mémoriserait l'en-tête et refuserait ensuite le HTTP local).
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if get_settings().environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response

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
