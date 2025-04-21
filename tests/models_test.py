from datetime import date
import pytest

from models import HeaderAnalysis

@pytest.mark.parametrize("due_date, expected", [
    ("2023-10-01", date(2023, 10, 1)),
    ("", None),
    (None, None),
])
def test_due_date(due_date, expected):
    # Create an instance of HeaderAnalysis with the test due_date
    header_analysis = HeaderAnalysis(
        clean_subject="Test Subject",
        is_important=True,
        is_transactional=False,
        due_date=due_date,
        notify=True,
        needs_analysis=False,
        analysis_reason=""
    )

    # Assert that the due_date is as expected
    assert header_analysis.due_date == expected

@pytest.mark.parametrize("due_date, exception", [
    ("2023-10-01 12:00:00.000000-05:00", ValueError),
    ("2023/10/01", ValueError),
    ("2023-13-01", ValueError),
    ("not a date", ValueError),
])
def test_due_date_invalid(due_date, exception):
    with pytest.raises(exception):
        # Create an instance of HeaderAnalysis with the test due_date
        header_analysis = HeaderAnalysis(
            clean_subject="Test Subject",
            is_important=True,
            is_transactional=False,
            due_date=due_date,
            notify=True,
            needs_analysis=False,
            analysis_reason=""
        )
