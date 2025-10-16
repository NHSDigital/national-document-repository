from typing import List

from lambdas.enums.trace_status import TraceStatus
from lambdas.models.stitch_trace import StitchTrace
from lambdas.tests.unit.conftest import TEST_NHS_NUMBER


def create_test_stitch_trace() -> StitchTrace:
    """Create a test StitchTrace object with optional overrides."""
    stitch_trace = StitchTrace(
        nhs_number=TEST_NHS_NUMBER, expire_at=9999999, job_status=TraceStatus.PENDING
    )
    return stitch_trace


def get_list_test_stitch_trace() -> List[StitchTrace]:
    """Create a list of test StitchTrace objects."""
    return [
        StitchTrace(
            nhs_number=TEST_NHS_NUMBER,
            expire_at=9999999,
            job_status=TraceStatus.PENDING,
        ),
        StitchTrace(
            nhs_number=TEST_NHS_NUMBER,
            expire_at=8888888,
            job_status=TraceStatus.PENDING,
        ),
        StitchTrace(
            nhs_number=TEST_NHS_NUMBER,
            expire_at=7777777,
            job_status=TraceStatus.PENDING,
        ),
    ]
