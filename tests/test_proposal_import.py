"""Tests for bulk proposal import (scraper file -> DRAFT proposals)."""

import csv
import io
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.proposals.models import Client, Platform, Proposal, ProposalStatus, Tag
from apps.proposals.services import ImportResult, ProposalImportService


# --------------------------------------------------------------------------- #
# Helpers to build uploaded files in each supported format
# --------------------------------------------------------------------------- #
def _json_file(rows, name="proposals.json"):
    return SimpleUploadedFile(
        name, json.dumps(rows).encode("utf-8"), content_type="application/json"
    )


def _csv_file(header, data_rows, name="proposals.csv"):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in data_rows:
        writer.writerow(row)
    return SimpleUploadedFile(
        name, buf.getvalue().encode("utf-8"), content_type="text/csv"
    )


def _xlsx_file(header, data_rows, name="proposals.xlsx"):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for row in data_rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile(
        name,
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _md_file(text, name="proposals.md"):
    return SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/markdown")


# --------------------------------------------------------------------------- #
# Parsing per format
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestParse:
    def test_parse_json_list(self):
        f = _json_file(
            [
                {"title": "A", "client": "Acme", "amount": "100.00"},
                {"title": "B"},
            ]
        )
        rows = ProposalImportService.parse(f)
        assert len(rows) == 2
        assert rows[0]["title"] == "A"
        assert rows[0]["client"] == "Acme"

    def test_parse_json_single_object(self):
        f = _json_file({"title": "Solo"})
        rows = ProposalImportService.parse(f)
        assert len(rows) == 1
        assert rows[0]["title"] == "Solo"

    def test_parse_csv_export_headers(self):
        f = _csv_file(
            ["Title", "Client", "Platform", "Amount", "Sent Date"],
            [["A", "Acme", "Upwork", "100", "2026-01-15"]],
        )
        rows = ProposalImportService.parse(f)
        assert rows[0]["title"] == "A"
        assert rows[0]["client"] == "Acme"
        assert rows[0]["platform"] == "Upwork"
        assert rows[0]["sent_date"] == "2026-01-15"

    def test_parse_xlsx(self):
        f = _xlsx_file(
            ["Title", "Client", "Amount"],
            [["A", "Acme", 250]],
        )
        rows = ProposalImportService.parse(f)
        assert rows[0]["title"] == "A"
        assert rows[0]["client"] == "Acme"

    def test_parse_markdown_table(self):
        md = (
            "# Scraped proposals\n\n"
            "| Title | Client | Amount |\n"
            "| --- | --- | --- |\n"
            "| A | Acme | 100 |\n"
            "| B | Globex | 200 |\n"
        )
        rows = ProposalImportService.parse(_md_file(md))
        assert len(rows) == 2
        assert rows[0]["title"] == "A"
        assert rows[1]["client"] == "Globex"

    def test_parse_unsupported_extension(self):
        f = SimpleUploadedFile("data.txt", b"nope", content_type="text/plain")
        with pytest.raises(ValueError):
            ProposalImportService.parse(f)


# --------------------------------------------------------------------------- #
# Importing rows
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestImport:
    def test_creates_drafts(self, user):
        f = _json_file(
            [{"title": "A", "client": "Acme"}, {"title": "B", "client": "Globex"}]
        )
        result = ProposalImportService.import_file(user, f)
        assert isinstance(result, ImportResult)
        assert result.created == 2
        assert result.skipped == 0
        assert not result.errors
        assert Proposal.objects.for_user(user).count() == 2
        for p in Proposal.objects.for_user(user):
            assert p.status == ProposalStatus.DRAFT
            assert p.owner == user

    def test_status_forced_to_draft(self, user):
        f = _json_file([{"title": "A", "status": "sent"}])
        ProposalImportService.import_file(user, f)
        assert Proposal.objects.get(title="A").status == ProposalStatus.DRAFT

    def test_creates_client_and_tags_by_name(self, user):
        f = _json_file(
            [{"title": "A", "client": "New Client", "tags": ["urgent", "web"]}]
        )
        ProposalImportService.import_file(user, f)
        assert Client.objects.filter(owner=user, name="New Client").exists()
        assert Tag.objects.filter(owner=user).count() == 2
        assert Proposal.objects.get(title="A").tags.count() == 2

    def test_platform_label_and_unknown(self, user):
        f = _json_file(
            [
                {"title": "bylabel", "platform": "Upwork"},
                {"title": "byvalue", "platform": "fiverr"},
                {"title": "unknown", "platform": "Nonsense"},
            ]
        )
        ProposalImportService.import_file(user, f)
        assert Proposal.objects.get(title="bylabel").platform == Platform.UPWORK
        assert Proposal.objects.get(title="byvalue").platform == Platform.FIVERR
        assert Proposal.objects.get(title="unknown").platform == Platform.OTHER

    def test_skips_duplicates(self, user, client_model):
        Proposal.objects.create(
            owner=user, title="Existing", client=client_model, amount=10
        )
        f = _json_file(
            [
                {"title": "Existing", "client": "Test Client"},
                {"title": "Brand New", "client": "Test Client"},
            ]
        )
        result = ProposalImportService.import_file(user, f)
        assert result.created == 1
        assert result.skipped == 1
        assert Proposal.objects.for_user(user).count() == 2

    def test_missing_title_reported_others_imported(self, user):
        f = _json_file([{"client": "Acme"}, {"title": "Valid"}])
        result = ProposalImportService.import_file(user, f)
        assert result.created == 1
        assert len(result.errors) == 1
        assert Proposal.objects.filter(title="Valid").exists()

    def test_invalid_amount_reported(self, user):
        f = _json_file([{"title": "Bad", "amount": "not-a-number"}, {"title": "Good"}])
        result = ProposalImportService.import_file(user, f)
        assert result.created == 1
        assert len(result.errors) == 1
        assert not Proposal.objects.filter(title="Bad").exists()

    def test_user_isolation(self, user, other_user):
        # other_user already has a proposal with the same title
        Proposal.objects.create(owner=other_user, title="Shared")
        f = _json_file([{"title": "Shared"}])
        result = ProposalImportService.import_file(user, f)
        # not a duplicate for `user`; gets created and stays scoped
        assert result.created == 1
        assert Proposal.objects.for_user(user).filter(title="Shared").count() == 1
        assert Proposal.objects.for_user(other_user).filter(title="Shared").count() == 1


# --------------------------------------------------------------------------- #
# View
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestImportView:
    def test_get_requires_login(self, client):
        resp = client.get(reverse("proposal-import"))
        assert resp.status_code == 302

    def test_get_renders_for_authed(self, authed_client):
        resp = authed_client.get(reverse("proposal-import"))
        assert resp.status_code == 200

    def test_post_creates_drafts_and_redirects(self, authed_client, user):
        f = _json_file([{"title": "Imported A"}, {"title": "Imported B"}])
        resp = authed_client.post(reverse("proposal-import"), {"file": f})
        assert resp.status_code == 302
        assert "status=draft" in resp.url
        assert Proposal.objects.for_user(user).count() == 2

    def test_post_invalid_extension_rejected(self, authed_client, user):
        f = SimpleUploadedFile("data.txt", b"nope", content_type="text/plain")
        resp = authed_client.post(reverse("proposal-import"), {"file": f})
        assert resp.status_code == 200
        assert Proposal.objects.for_user(user).count() == 0
