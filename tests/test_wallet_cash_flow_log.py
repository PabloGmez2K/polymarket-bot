from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "wallet_cash_flow_log.py"
START = "2026-05-06T00:00:00Z"
END = "2026-05-06T01:00:00Z"


def run_cli(*args: str, input_text: str | None = None, data_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(TOOL_PATH), *args]
    if data_dir is not None:
        command.extend(["--data-dir", str(data_dir)])
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        input=input_text,
        capture_output=True,
        timeout=30,
    )


def ledger_path(data_dir: Path) -> Path:
    return data_dir / "wallet_cash_flows.jsonl"


def load_rows(data_dir: Path) -> list[dict]:
    return [json.loads(line) for line in ledger_path(data_dir).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(data_dir: Path, rows: list[dict]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    ledger_path(data_dir).write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def valid_row(entry_id: str | None = None, **extra) -> dict:
    row = {
        "schema_version": 2,
        "entry_id": entry_id or str(uuid.uuid4()),
        "recorded_at": "2026-05-06T00:00:00Z",
        "actor": "pablo_manual",
        "type": "no_cash_flow_attestation",
        "period_start": START,
        "period_end": END,
    }
    row.update(extra)
    return row


def append_attestation_args(*extra: str) -> tuple[str, ...]:
    return (
        "append",
        "--type",
        "no_cash_flow_attestation",
        "--period-start",
        START,
        "--period-end",
        END,
        *extra,
    )


def append_deposit_args(*extra: str) -> tuple[str, ...]:
    return (
        "append",
        "--type",
        "deposit",
        "--period-start",
        START,
        "--period-end",
        END,
        "--amount-usdc",
        "12.34",
        *extra,
    )


def test_help_works():
    result = run_cli("--help")

    assert result.returncode == 0
    assert "append" in result.stdout
    assert "validate" in result.stdout
    assert "show" in result.stdout


def test_dry_run_default_no_write(tmp_path):
    result = run_cli(*append_deposit_args(), data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "DRY-RUN: row NOT written." in result.stdout
    assert not ledger_path(tmp_path).exists()


def test_append_without_write_does_not_create_file(tmp_path):
    result = run_cli(*append_attestation_args(), data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    assert not ledger_path(tmp_path).exists()


def test_write_without_init_fails_if_file_missing(tmp_path):
    result = run_cli(*append_deposit_args("--write"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "use --write --init" in result.stderr
    assert not ledger_path(tmp_path).exists()


def test_init_without_write_fails(tmp_path):
    result = run_cli(*append_deposit_args("--init"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "--init is only valid with --write" in result.stderr
    assert not ledger_path(tmp_path).exists()


def test_write_init_with_confirmation_creates_file_in_tmp_path(tmp_path):
    result = run_cli(*append_deposit_args("--write", "--init"), input_text="YES I CONFIRM\n", data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    rows = load_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["type"] == "deposit"


def test_write_init_without_confirmation_fails(tmp_path):
    result = run_cli(*append_deposit_args("--write", "--init"), input_text="NO\n", data_dir=tmp_path)

    assert result.returncode != 0
    assert "confirmation failed" in result.stderr
    assert not ledger_path(tmp_path).exists()


def test_yes_allows_noninteractive_init(tmp_path):
    result = run_cli(*append_deposit_args("--write", "--init", "--yes"), data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(load_rows(tmp_path)) == 1


def test_validate_read_only(tmp_path):
    result = run_cli("validate", data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "missing" in result.stdout
    assert not ledger_path(tmp_path).exists()


def test_show_read_only(tmp_path):
    result = run_cli("show", "--last", "5", data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "missing" in result.stdout
    assert not ledger_path(tmp_path).exists()


def test_entry_id_auto_generated_uuid4(tmp_path):
    result = run_cli(*append_deposit_args("--json"), data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    parsed = uuid.UUID(payload["row"]["entry_id"])
    assert parsed.version == 4


def test_actor_hardcoded_pablo_manual(tmp_path):
    result = run_cli(*append_deposit_args("--json"), data_dir=tmp_path)

    payload = json.loads(result.stdout)
    assert payload["row"]["actor"] == "pablo_manual"


def test_schema_version_2(tmp_path):
    result = run_cli(*append_deposit_args("--json"), data_dir=tmp_path)

    payload = json.loads(result.stdout)
    assert payload["row"]["schema_version"] == 2


def test_reject_example_entry_id_override(tmp_path):
    result = run_cli(*append_deposit_args("--entry-id", "EXAMPLE-001"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "EXAMPLE-" in result.stderr
    assert not ledger_path(tmp_path).exists()


def test_reject_forbidden_types(tmp_path):
    for flow_type in ("inferred", "auto", "reconstructed", "estimated"):
        result = run_cli(
            "append",
            "--type",
            flow_type,
            "--period-start",
            START,
            "--period-end",
            END,
            data_dir=tmp_path,
        )
        assert result.returncode != 0
        assert "forbidden" in result.stderr


def test_reject_adjustment_without_note(tmp_path):
    result = run_cli(
        "append",
        "--type",
        "adjustment",
        "--period-start",
        START,
        "--period-end",
        END,
        "--amount-usdc",
        "0",
        "--reviewed-by-opus",
        "--confirm-adjustment",
        data_dir=tmp_path,
    )

    assert result.returncode != 0
    assert "note" in result.stderr


def test_reject_adjustment_without_reviewed_by_opus(tmp_path):
    result = run_cli(
        "append",
        "--type",
        "adjustment",
        "--period-start",
        START,
        "--period-end",
        END,
        "--amount-usdc",
        "0",
        "--note",
        "manual correction",
        "--confirm-adjustment",
        data_dir=tmp_path,
    )

    assert result.returncode != 0
    assert "--reviewed-by-opus" in result.stderr


def test_reject_adjustment_without_confirm_adjustment(tmp_path):
    result = run_cli(
        "append",
        "--type",
        "adjustment",
        "--period-start",
        START,
        "--period-end",
        END,
        "--amount-usdc",
        "0",
        "--note",
        "manual correction",
        "--reviewed-by-opus",
        data_dir=tmp_path,
    )

    assert result.returncode != 0
    assert "--confirm-adjustment" in result.stderr


def test_reject_no_cash_flow_attestation_with_amount(tmp_path):
    result = run_cli(*append_attestation_args("--amount-usdc", "1"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "must not include amount_usdc" in result.stderr


def test_reject_corrupt_existing_jsonl(tmp_path):
    ledger_path(tmp_path).write_text("{not-json}\n", encoding="utf-8")

    result = run_cli(*append_deposit_args("--write"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "corrupt JSONL" in result.stderr
    assert ledger_path(tmp_path).read_text(encoding="utf-8") == "{not-json}\n"


def test_reject_invalid_existing_schema_version(tmp_path):
    write_rows(tmp_path, [valid_row(schema_version=1)])

    result = run_cli(*append_deposit_args("--write"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "schema_version must be 2" in result.stderr
    assert len(load_rows(tmp_path)) == 1


def test_reject_duplicate_entry_id_in_existing_file(tmp_path):
    duplicate = str(uuid.uuid4())
    write_rows(tmp_path, [valid_row(entry_id=duplicate), valid_row(entry_id=duplicate)])

    result = run_cli(*append_deposit_args("--write"), data_dir=tmp_path)

    assert result.returncode != 0
    assert "duplicate entry_id" in result.stderr
    assert len(load_rows(tmp_path)) == 2


def test_append_valid_preserves_append_only(tmp_path):
    original = valid_row()
    write_rows(tmp_path, [original])

    result = run_cli(*append_deposit_args("--write"), data_dir=tmp_path)

    assert result.returncode == 0, result.stderr
    rows = load_rows(tmp_path)
    assert rows[0] == original
    assert len(rows) == 2
    assert rows[1]["entry_id"] != original["entry_id"]


def test_recorded_at_is_iso_utc(tmp_path):
    result = run_cli(*append_deposit_args("--json"), data_dir=tmp_path)

    payload = json.loads(result.stdout)
    recorded_at = payload["row"]["recorded_at"]
    assert recorded_at.endswith("Z")
    parsed = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    assert parsed.tzinfo == timezone.utc
