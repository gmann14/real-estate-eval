"""Tests for the CLI entry."""
from __future__ import annotations

from pathlib import Path

import pytest

from tax_sale.cli import build_parser, main


def test_parser_requires_subcommand():
    """Without a subcommand the parser should error out."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_bidsheet_args():
    parser = build_parser()
    args = parser.parse_args(["bidsheet", "--year", "2026", "--lot", "2", "--ceiling", "45000"])
    assert args.cmd == "bidsheet"
    assert args.year == 2026
    assert args.lot == 2
    assert args.ceiling == 45000.0


def test_parser_bidsheet_all_args():
    parser = build_parser()
    args = parser.parse_args([
        "bidsheet-all", "--year", "2025", "--ceiling", "30000",
        "--out-dir", "/tmp/foo",
    ])
    assert args.cmd == "bidsheet-all"
    assert args.year == 2025
    assert args.ceiling == 30000.0
    assert args.out_dir == Path("/tmp/foo")


def test_parser_backtest_default_kind():
    parser = build_parser()
    args = parser.parse_args(["backtest"])
    assert args.cmd == "backtest"
    assert args.kind == "both"


def test_parser_backtest_explicit_kind():
    parser = build_parser()
    args = parser.parse_args(["backtest", "--kind", "exceedance"])
    assert args.kind == "exceedance"


def test_parser_stats_no_args():
    parser = build_parser()
    args = parser.parse_args(["stats"])
    assert args.cmd == "stats"


def test_parser_accepts_strict_flag():
    parser = build_parser()
    args = parser.parse_args(["stats", "--strict"])
    assert args.strict is True


def test_cli_bidsheet_missing_lot_returns_nonzero(capsys):
    """If the requested year/lot doesn't exist in the dataset, exit 1 with stderr."""
    code = main(["bidsheet", "--year", "1900", "--lot", "9999"])
    assert code == 1
    err = capsys.readouterr().err
    assert "No lot found" in err


def test_cli_stats_runs(capsys):
    code = main(["stats"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Total lot records" in out
    assert "Outcomes" in out


def test_cli_bidsheet_writes_to_stdout(capsys):
    code = main(["bidsheet", "--year", "2026", "--lot", "2"])
    assert code == 0
    out = capsys.readouterr().out
    assert "MODL-2026-2" in out


def test_cli_bidsheet_all_writes_to_outdir(tmp_path, capsys):
    out_dir = tmp_path / "bidsheets"
    code = main([
        "bidsheet-all", "--year", "2026", "--ceiling", "50000",
        "--out-dir", str(out_dir),
    ])
    assert code == 0
    files = list(out_dir.glob("lot-*.md"))
    assert len(files) > 0
    # Each file should contain a bid sheet header
    for f in files[:3]:
        content = f.read_text()
        assert "MODL-2026" in content


def test_cli_bidsheet_all_unknown_year_errors(capsys):
    code = main(["bidsheet-all", "--year", "1900"])
    assert code == 1
    assert "No lots found" in capsys.readouterr().err


def test_parser_enrichment_template_args():
    parser = build_parser()
    args = parser.parse_args([
        "enrichment-template", "--year", "2027",
        "--out", "/tmp/template.csv",
    ])
    assert args.cmd == "enrichment-template"
    assert args.year == 2027
    assert args.out == Path("/tmp/template.csv")


def test_cli_enrichment_template_writes_file(tmp_path):
    out_path = tmp_path / "template.csv"
    code = main([
        "enrichment-template", "--year", "2026", "--out", str(out_path),
    ])
    assert code == 0
    assert out_path.exists()
    lines = out_path.read_text().splitlines()
    # Header + at least a few rows
    assert "aan" in lines[0]
    assert "assessed_value" in lines[0]
    assert len(lines) > 1
