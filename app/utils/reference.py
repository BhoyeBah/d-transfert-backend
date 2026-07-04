import secrets

# Alphabet excluding visually ambiguous characters (0/O, 1/I).
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_reference(prefix: str, length: int = 8) -> str:
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}-{suffix}"


def generate_company_registration_code() -> str:
    return generate_reference("DT")


def generate_operation_reference() -> str:
    return generate_reference("OP")


def generate_entry_reference() -> str:
    return generate_reference("EN")
