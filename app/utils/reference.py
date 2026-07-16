import re
import secrets
import unicodedata
from datetime import date

# Alphabet excluding visually ambiguous characters (0/O, 1/I).
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

# Laisse de la marge pour le suffixe de désambiguïsation ("-2", "-3", ...) et le suffixe
# d'employé ("-EMP001") tout en restant dans la limite de la colonne (String(32)).
_COMPANY_SLUG_MAX_LENGTH = 20


def slugify_company_name(name: str) -> str:
    """Ex. "GK BUSINESS" -> "gk-business". Retourne "" si le nom ne contient aucun caractère
    alphanumérique exploitable (ex. uniquement des symboles ou des idéogrammes)."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:_COMPANY_SLUG_MAX_LENGTH].strip("-")


def generate_reference(prefix: str, length: int = 8) -> str:
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}-{suffix}"


def daily_sequence_prefix(prefix: str, on_date: date) -> str:
    """Préfixe 'OP-09-07-26-' identifiant le jour, pour compter les références déjà émises."""
    return f"{prefix}-{on_date:%d-%m-%y}-"


def format_daily_reference(prefix: str, on_date: date, sequence: int) -> str:
    """Référence journalière séquentielle par entreprise, ex. OP-09-07-26-0001."""
    return f"{daily_sequence_prefix(prefix, on_date)}{sequence:04d}"


def generate_company_registration_code() -> str:
    return generate_reference("DT")


def generate_employee_matricule(company_registration_code: str, sequence: int) -> str:
    return f"{company_registration_code}-EMP{sequence:03d}"


def generate_platform_admin_matricule() -> str:
    return generate_reference("SA")
