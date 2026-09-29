from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

from skills.traction_tables import _block_rows, _incremental_rows, display_traction_tables, source_traction_tables


def test_incremental_revenue_uses_full_source_horizon_and_excludes_tobe():
    rows = [
        ["Increment P&L, mR", "2026", "2027", "2028", "2029", "2030", "2031", "", "2026-31 total"],
        ["Revenue", "86", "379", "626", "817", "936", "1 012", "", "3 857"],
        ["ToBe P&L, mR", "2026", "2027", "2028", "2029", "2030", "2031", "", "2026-31 total"],
        ["Revenue", "298", "573", "824", "1 031", "1 168", "1 249", "", "5 144"],
    ]
    candidates = _incremental_rows(rows)
    assert len(candidates) == 1
    _score, table = candidates[0]
    assert table["periods"] == ["2026", "2027", "2028", "2029", "2030", "2031", "2026-31 total"]
    assert table["rows"][0]["values"] == ["86", "379", "626", "817", "936", "1 012", "3 857"]


def test_dtb_and_revenue_keep_independent_periods():
    revenue = _incremental_rows([
        ["Incremental revenue, mR", "2026", "2027", "2026-27 total"],
        ["Revenue", "10", "20", "30"],
    ])[0][1]
    dtb = _incremental_rows([
        ["Incremental DTB, %", "CY26", "CY27", "CY28", "Total"],
        ["DTB", "1%", "2%", "3%", "2%"],
    ])[0][1]
    rendered = display_traction_tables([revenue, dtb], language="ru")
    assert [table["metric"] for table in rendered["tables"]] == ["revenue", "dtb"]
    assert len(rendered["tables"][0]["periods"]) == 3
    assert len(rendered["tables"][1]["periods"]) == 4
    assert rendered["tables"][1]["rows"][0]["values"] == ["1%", "2%", "3%", "2%"]


def test_legacy_markdown_table_rows_are_read_without_reparse():
    block = {
        "markdown": "| Increment P&L, mR | 2026 | 2027 | 2026-27 total |\n"
        "| --- | --- | --- | --- |\n"
        "| Revenue | 1 | 2 | 3 |",
        "metadata": {"extractor": "pdfplumber"},
    }
    assert _incremental_rows(_block_rows(block))[0][1]["rows"][0]["values"] == ["1", "2", "3"]


def test_previous_scenario_is_not_used_as_current_incremental_data():
    assert _incremental_rows([
        ["Diff vs IC 25, mR", "2026", "2027", "Total"],
        ["Revenue", "-1", "-2", "-3"],
    ]) == []


def test_source_tables_use_matching_owned_artifact_and_ignore_stale_parse(tmp_path, monkeypatch):
    import app.core.config as config

    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(storage_root=tmp_path))
    document = SimpleNamespace(
        owner_id=uuid4(), document_id=uuid4(), parsed_text="Parsed source", file_hash_sha256="a" * 64
    )
    document.id = document.document_id
    parsed_dir = tmp_path / "documents" / str(document.owner_id) / str(document.id) / "parsed"
    parsed_dir.mkdir(parents=True)
    artifact = {
        "source": {"sha256": document.file_hash_sha256},
        "outputs": {"plain_text_sha256": hashlib.sha256(document.parsed_text.encode()).hexdigest()},
        "blocks": [{
            "id": "b0014", "type": "table", "page": 14,
            "metadata": {"rows": [
                ["Increment P&L, mR", "2026", "2027", "2026-27 total"],
                ["Revenue", "86", "379", "465"],
            ]},
        }],
    }
    (parsed_dir / "structured.json").write_text(json.dumps(artifact))
    tables = source_traction_tables(document)
    assert tables[0]["source_page"] == 14
    assert tables[0]["rows"][0]["values"] == ["86", "379", "465"]
    document.file_hash_sha256 = "b" * 64
    assert source_traction_tables(document) == []
