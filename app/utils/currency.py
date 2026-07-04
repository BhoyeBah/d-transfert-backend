SUPPORTED_CURRENCIES = frozenset({"XOF", "GNF", "USD", "EUR"})


def is_supported_currency(code: str) -> bool:
    return code.upper() in SUPPORTED_CURRENCIES
