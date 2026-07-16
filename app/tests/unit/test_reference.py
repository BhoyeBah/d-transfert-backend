from datetime import date

from app.utils.reference import (
    daily_sequence_prefix,
    format_daily_reference,
    generate_reference,
    slugify_company_name,
)


def test_daily_sequence_prefix_formats_date():
    assert daily_sequence_prefix("OP", date(2026, 7, 9)) == "OP-09-07-26-"


def test_format_daily_reference_pads_sequence():
    assert format_daily_reference("OP", date(2026, 7, 9), 1) == "OP-09-07-26-0001"
    assert format_daily_reference("OP", date(2026, 7, 9), 42) == "OP-09-07-26-0042"


def test_generate_reference_uses_prefix_and_length():
    reference = generate_reference("DT")
    prefix, suffix = reference.split("-")
    assert prefix == "DT"
    assert len(suffix) == 8


def test_slugify_company_name_basic():
    assert slugify_company_name("GK BUSINESS") == "gk-business"


def test_slugify_company_name_strips_accents_and_symbols():
    assert slugify_company_name("Société Générale") == "societe-generale"
    assert slugify_company_name("A&B Corp. (Import/Export)") == "a-b-corp-import-expo"


def test_slugify_company_name_collapses_whitespace():
    assert slugify_company_name("  Multi   Espaces!! ") == "multi-espaces"


def test_slugify_company_name_truncates_to_max_length():
    slug = slugify_company_name("Une Entreprise Avec Un Nom Vraiment Tres Long")
    assert len(slug) <= 20
    assert not slug.endswith("-")


def test_slugify_company_name_returns_empty_for_non_latin_script():
    assert slugify_company_name("日本語会社") == ""
