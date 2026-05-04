"""
truth_pipeline_schema.py — Aplicador idempotente de schema v2 (Fase 1 Truth Pipeline).

Solo librería estándar. Sin dependencias externas. No importa bot.py.
No toca tablas v1 (cycle_events, market_snapshots, forecast_snapshots).

Uso:
    python tools/truth_pipeline_schema.py --db data/polymarket.db [--dry-run]

Salida JSON:
    {"status": "applied"|"already_applied"|"dry_run"|"error", "version": 2, ...}

Exit codes:
    0 — aplicado o ya aplicado
    1 — error (DB inaccesible, schema_version=1 no encontrado, error SQL)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_TARGET_VERSION = 2
_REQUIRED_BASE_VERSION = 1

# Ruta del SQL relativa a este script
_SQL_PATH = Path(__file__).parent.parent / "sql" / "002_truth_pipeline.sql"


def _split_sql_statements(sql: str) -> list[str]:
    """Divide un script SQL en sentencias ejecutables individuales.

    Filtra comentarios de línea (--) y sentencias vacías. Soporta CREATE VIEW
    que incluyen AS SELECT con punto y coma interno — divide solo en ;
    al nivel de la línea.
    """
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)
    return statements


def _load_sql() -> str:
    if not _SQL_PATH.exists():
        raise FileNotFoundError(f"SQL file not found: {_SQL_PATH}")
    return _SQL_PATH.read_text(encoding="utf-8")


def _get_schema_version(conn: sqlite3.Connection) -> int | None:
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] if row and row[0] is not None else None
    except sqlite3.OperationalError:
        return None


def apply_schema(db_path: str, dry_run: bool = False) -> dict:
    """Aplica sql/002_truth_pipeline.sql de forma idempotente.

    Returns dict con status, version y detalles.
    """
    try:
        sql = _load_sql()
    except FileNotFoundError as exc:
        return {"status": "error", "version": _TARGET_VERSION, "error": str(exc)}

    if dry_run:
        return {
            "status": "dry_run",
            "version": _TARGET_VERSION,
            "sql_preview": sql[:200] + "..." if len(sql) > 200 else sql,
            "db_path": db_path,
        }

    try:
        # isolation_level=None → autocommit; gestionamos BEGIN/COMMIT explícitamente
        conn = sqlite3.connect(db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError as exc:
        return {"status": "error", "version": _TARGET_VERSION, "error": str(exc)}

    try:
        current_version = _get_schema_version(conn)

        if current_version is None:
            # DB nueva o sin tabla schema_version — aplicar desde cero
            pass
        elif current_version < _REQUIRED_BASE_VERSION:
            conn.close()
            return {
                "status": "error",
                "version": _TARGET_VERSION,
                "error": f"Base schema_version={current_version} < required {_REQUIRED_BASE_VERSION}",
            }
        elif current_version >= _TARGET_VERSION:
            conn.close()
            return {
                "status": "already_applied",
                "version": _TARGET_VERSION,
                "current_version": current_version,
            }

        # Aplicar dentro de una transacción explícita.
        # No usamos executescript() porque emite COMMIT implícito antes de
        # ejecutar, lo que puede causar comportamientos inesperados con WAL
        # en Python 3.12+. En su lugar parseamos por sentencias y ejecutamos
        # en una sola transacción explícita.
        statements = _split_sql_statements(sql)
        conn.execute("BEGIN")
        try:
            for stmt in statements:
                conn.execute(stmt)
            conn.execute("COMMIT")
        except sqlite3.Error:
            conn.execute("ROLLBACK")
            raise

        final_version = _get_schema_version(conn)
        conn.close()
        return {
            "status": "applied",
            "version": _TARGET_VERSION,
            "current_version": final_version,
        }

    except sqlite3.Error as exc:
        try:
            conn.close()
        except Exception:
            pass
        return {"status": "error", "version": _TARGET_VERSION, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aplica schema v2 (Truth Pipeline) a polymarket.db"
    )
    parser.add_argument("--db", required=True, help="Ruta a polymarket.db")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el SQL pero no lo ejecuta",
    )
    args = parser.parse_args()

    result = apply_schema(args.db, dry_run=args.dry_run)
    print(json.dumps(result))
    return 0 if result["status"] in ("applied", "already_applied", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
