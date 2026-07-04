import secrets

# Alphabet excluding visually ambiguous characters (0/O, 1/I).
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_reference(prefix: str, length: int = 8) -> str:
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}-{suffix}"


def generate_company_registration_code() -> str:
    return generate_reference("DT")


def generate_employee_matricule(company_registration_code: str, sequence: int) -> str:
    return f"{company_registration_code}-EMP{sequence:03d}"


def generate_operation_reference() -> str:
    return generate_reference("OP")


def generate_entry_reference() -> str:
    return generate_reference("EN")


def generate_transfer_reference() -> str:
    return generate_reference("TR")


def generate_payment_reference() -> str:
    return generate_reference("PA")


def generate_supplier_movement_reference() -> str:
    return generate_reference("SR")
