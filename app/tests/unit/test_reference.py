from datetime import date

from app.utils.reference import daily_sequence_prefix, format_daily_reference, generate_reference


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
