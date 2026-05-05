"""
truth_pipeline_runner.py — Writer standalone para Truth Pipeline (Fase 1A.3).

Sin imports de bot.py. Solo stdlib + truth_pipeline_schema + truth_pipeline_fetcher.
Default OFF: requiere env var TRUTH_PIPELINE_ENABLED activa, si no sale no-op (salvo --dry-run).

Modos:
  A) --input-json <path>: lee fixture JSON sin red (tests, replay manual)
  B) --city <city> --date <YYYY-MM-DD>: llama al fetcher en memoria

Flags:
  --db <path>   ruta a la DB (requerida para escribir; omitible en --dry-run)
  --dry-run     muestra qué escribiría, sin abrir DB ni escribir

Idempotencia (implementada en Python, sin UNIQUE constraint en DB):
  Clave lógica: (city, date_iso, observed_source).
  Si el registro ya existe y cambia observed_high_c o resolution_outcome,
  se actualiza el campo y se añade una fila a truth_revisions por campo cambiado.

Tablas escritas: truth_records, truth_revisions.
Tablas solo leídas: forecast_snapshots (enriquecimiento forecast_high_c).
Tablas nunca tocadas: cycle_events, market_snapshots.

Exit codes:
  0 — ok, no-op, o dry-run
  1 — error (DB inaccesible, JSON inválido, etc.)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
_tools_dir = str(REPO_ROOT / "tools")
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

from truth_pipeline_schema import apply_schema  # noqa: E402
from truth_pipeline_fetcher import fetch_observed_high  # noqa: E402

# Campos de truth_records que se auditan en truth_revisions ante cambios
_TRACKED_FIELDS = ("observed_high_c", "resolution_outcome")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_record(raw: dict) -> dict:
    """Normaliza un registro crudo (fetcher o fixture) al layout de truth_records."""
    # Fetcher usa 'date'; fixtures pueden usar 'date_iso'
    date_iso = raw.get("date_iso") or raw.get("date")
    # Fetcher usa 'source'; schema usa 'observed_source'
    observed_source = raw.get("observed_source") or raw.get("source")
    return {
        "city": raw.get("city"),
        "date_iso": date_iso,
        "condition": raw.get("condition"),
        "threshold_c": raw.get("threshold_c"),
        "question": raw.get("question"),
        "market_id": raw.get("market_id"),
        "token_id_yes": raw.get("token_id_yes"),
        "token_id_no": raw.get("token_id_no"),
        "forecast_high_c": raw.get("forecast_high_c"),
        "forecast_source": raw.get("forecast_source"),
        "observed_high_c": raw.get("observed_high_c"),
        "observed_source": observed_source,
        "resolution_outcome": raw.get("resolution_outcome", "UNKNOWN"),
        "resolution_ts_utc": raw.get("resolution_ts_utc"),
        "resolution_method": raw.get("resolution_method"),
        "bot_had_position": int(raw.get("bot_had_position") or 0),
        "bot_side": raw.get("bot_side"),
        "snapshot_ts_utc": raw.get("snapshot_ts_utc") or _now_utc(),
        "payload_json": json.dumps(raw, ensure_ascii=False),
    }


def _lookup_snapshot(
    conn: sqlite3.Connection, city: str, date_iso: str
) -> dict | None:
    """Lee el forecast snapshot más reciente para (city, date_iso). Solo lectura."""
    try:
        row = conn.execute(
            "SELECT forecast_high_c, source FROM forecast_snapshots "
            "WHERE city=? AND target_date=? ORDER BY ts_utc DESC LIMIT 1",
            (city, date_iso),
        ).fetchone()
    except sqlite3.OperationalError:
        # forecast_snapshots ausente no es error fatal
        return None
    if row:
        return {"forecast_high_c": row[0], "forecast_source": row[1]}
    return None


def _find_existing(
    conn: sqlite3.Connection,
    city: str,
    date_iso: str,
    observed_source: str | None,
) -> dict | None:
    """Busca registro existente por clave de idempotencia (city, date_iso, observed_source)."""
    if observed_source is not None:
        row = conn.execute(
            "SELECT id, observed_high_c, resolution_outcome "
            "FROM truth_records WHERE city=? AND date_iso=? AND observed_source=?",
            (city, date_iso, observed_source),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, observed_high_c, resolution_outcome "
            "FROM truth_records WHERE city=? AND date_iso=? AND observed_source IS NULL",
            (city, date_iso),
        ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "observed_high_c": row[1], "resolution_outcome": row[2]}


def _insert_record(conn: sqlite3.Connection, rec: dict) -> int:
    cur = conn.execute(
        """INSERT INTO truth_records
           (city, date_iso, condition, threshold_c, question, market_id,
            token_id_yes, token_id_no, forecast_high_c, forecast_source,
            observed_high_c, observed_source, resolution_outcome,
            resolution_ts_utc, resolution_method, bot_had_position, bot_side,
            snapshot_ts_utc, payload_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            rec["city"], rec["date_iso"], rec["condition"], rec["threshold_c"],
            rec["question"], rec["market_id"], rec["token_id_yes"], rec["token_id_no"],
            rec["forecast_high_c"], rec["forecast_source"], rec["observed_high_c"],
            rec["observed_source"], rec["resolution_outcome"], rec["resolution_ts_utc"],
            rec["resolution_method"], rec["bot_had_position"], rec["bot_side"],
            rec["snapshot_ts_utc"], rec["payload_json"],
        ),
    )
    return cur.lastrowid


def _add_revision(
    conn: sqlite3.Connection,
    truth_id: int,
    field: str,
    old_val,
    new_val,
    reason: str = "runner_update",
) -> None:
    conn.execute(
        """INSERT INTO truth_revisions
           (truth_record_id, field_changed, old_value, new_value, revision_ts_utc, reason)
           VALUES (?,?,?,?,?,?)""",
        (
            truth_id,
            field,
            str(old_val) if old_val is not None else None,
            str(new_val) if new_val is not None else None,
            _now_utc(),
            reason,
        ),
    )


def _process_single(conn: sqlite3.Connection, rec: dict) -> dict:
    """Inserta o actualiza un registro en write mode (sin dry-run)."""
    city = rec["city"]
    date_iso = rec["date_iso"]
    observed_source = rec["observed_source"]

    # Enriquecer forecast_high_c desde forecast_snapshots si no viene en el input
    if rec["forecast_high_c"] is None:
        snap = _lookup_snapshot(conn, city, date_iso)
        if snap:
            rec["forecast_high_c"] = snap["forecast_high_c"]
            if rec["forecast_source"] is None:
                rec["forecast_source"] = snap.get("forecast_source")

    existing = _find_existing(conn, city, date_iso, observed_source)

    if existing is None:
        new_id = _insert_record(conn, rec)
        return {
            "action": "inserted",
            "id": new_id,
            "city": city,
            "date_iso": date_iso,
            "observed_high_c": rec["observed_high_c"],
        }

    # Detectar cambios en campos auditados
    changes = []
    for field in _TRACKED_FIELDS:
        old_val = existing[field]
        new_val = rec[field]
        if new_val is not None and old_val != new_val:
            changes.append((field, old_val, new_val))

    if not changes:
        return {
            "action": "no_change",
            "id": existing["id"],
            "city": city,
            "date_iso": date_iso,
        }

    for field, old_val, new_val in changes:
        _add_revision(conn, existing["id"], field, old_val, new_val)
        conn.execute(
            f"UPDATE truth_records SET {field}=? WHERE id=?",  # noqa: S608
            (new_val, existing["id"]),
        )

    return {
        "action": "updated",
        "id": existing["id"],
        "city": city,
        "date_iso": date_iso,
        "changes": [c[0] for c in changes],
    }


# ─── Función pública ──────────────────────────────────────────────────────────

def run(
    *,
    db_path: str | None,
    input_json: str | None,
    city: str | None,
    date_iso: str | None,
    dry_run: bool,
    enabled: bool,
) -> dict:
    """
    Lógica central del runner.

    enabled: refleja TRUTH_PIPELINE_ENABLED (pasado explícitamente para testabilidad).
    Retorna dict con status y lista de results.
    """
    # Guard principal: sin env var y sin dry-run → no-op inmediato
    if not enabled and not dry_run:
        return {
            "status": "no_op",
            "reason": "TRUTH_PIPELINE_ENABLED != 1",
            "dry_run": False,
        }

    # ── Obtener registros crudos ──────────────────────────────────────────────
    raw_records: list[dict] = []

    if input_json is not None:
        # Modo A: leer desde JSON (sin red)
        path = Path(input_json)
        if not path.exists():
            return {"status": "error", "reason": f"input-json not found: {input_json}"}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"status": "error", "reason": f"invalid JSON: {exc}"}
        if isinstance(data, dict):
            raw_records = [data]
        elif isinstance(data, list):
            raw_records = data
        else:
            return {"status": "error", "reason": "input-json must be object or array"}

    elif city and date_iso:
        # Modo B: fetcher en memoria
        # En dry-run no hacemos red (fetcher también en dry-run)
        result = fetch_observed_high(city, date_iso, dry_run=dry_run)
        raw_records = [result]

    else:
        return {
            "status": "error",
            "reason": "requiere --input-json o (--city + --date)",
        }

    # ── Clasificar registros ──────────────────────────────────────────────────
    processable: list[dict] = []
    skipped: list[dict] = []
    for r in raw_records:
        s = r.get("status")
        if s == "ok":
            processable.append(r)
        else:
            skipped.append({
                "action": "skipped",
                "city": r.get("city"),
                "date_iso": r.get("date_iso") or r.get("date"),
                "status": s,
            })

    # ── Dry-run: preview sin abrir DB ─────────────────────────────────────────
    if dry_run:
        preview = []
        for r in processable:
            rec = _normalize_record(r)
            preview.append({
                "action": "would_write",
                "city": rec["city"],
                "date_iso": rec["date_iso"],
                "observed_high_c": rec["observed_high_c"],
                "observed_source": rec["observed_source"],
                "resolution_outcome": rec["resolution_outcome"],
            })
        return {
            "status": "dry_run",
            "dry_run": True,
            "processable": len(processable),
            "skipped": len(skipped),
            "results": preview + skipped,
        }

    # ── Write mode ────────────────────────────────────────────────────────────
    if not db_path:
        return {"status": "error", "reason": "--db requerido para escribir"}

    # Aplicar schema v2 de forma idempotente antes de cualquier escritura
    schema_result = apply_schema(db_path)
    if schema_result["status"] == "error":
        return {
            "status": "error",
            "reason": f"schema error: {schema_result.get('error', 'unknown')}",
        }

    try:
        conn = sqlite3.connect(db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError as exc:
        return {"status": "error", "reason": f"cannot open DB: {exc}"}

    results: list[dict] = list(skipped)
    try:
        conn.execute("BEGIN")
        for r in processable:
            rec = _normalize_record(r)
            if not rec["city"] or not rec["date_iso"]:
                results.append({
                    "action": "skipped",
                    "reason": "missing city or date_iso",
                })
                continue
            results.append(_process_single(conn, rec))
        conn.execute("COMMIT")
    except sqlite3.Error as exc:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        conn.close()
        return {"status": "error", "reason": f"DB write error: {exc}"}

    conn.close()
    return {
        "status": "ok",
        "dry_run": False,
        "processable": len(processable),
        "skipped": len(skipped),
        "results": results,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Truth Pipeline runner — escribe truth_records/truth_revisions"
    )
    parser.add_argument("--db", default=None, help="Ruta a polymarket.db")
    parser.add_argument(
        "--input-json", default=None,
        help="Ruta a fixture JSON de entrada (Modo A, sin red)",
    )
    parser.add_argument("--city", default=None, help="Ciudad (Modo B, llama al fetcher)")
    parser.add_argument(
        "--date", dest="date_iso", default=None,
        help="Fecha ISO YYYY-MM-DD (Modo B)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Muestra qué escribiría sin abrir DB ni escribir",
    )
    args = parser.parse_args()

    enabled = os.environ.get("TRUTH_PIPELINE_ENABLED", "0") == "1"

    result = run(
        db_path=args.db,
        input_json=args.input_json,
        city=args.city,
        date_iso=args.date_iso,
        dry_run=args.dry_run,
        enabled=enabled,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in ("ok", "no_op", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
