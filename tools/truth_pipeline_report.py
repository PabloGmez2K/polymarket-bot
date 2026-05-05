"""
truth_pipeline_report.py — Reporter CLI standalone para Truth Pipeline (Fase 1A.4).

Lee una DB SQLite indicada por --db y reporta estadísticas de truth_records.
No importa bot.py. Solo stdlib. No actúa. Informativo por defecto.

Uso:
    python tools/truth_pipeline_report.py --db data/polymarket.db
    python tools/truth_pipeline_report.py --db data/polymarket.db --json

Estados de salida:
    schema_missing — truth_records no existe (schema v2 no aplicado)
    empty          — truth_records existe pero sin filas
    no_action      — datos sanos (calibración ≥50% o n_resolved<10)
    watch          — calibración <50% con n_resolved≥10, o cobertura baja
    watch_tech     — DB inaccesible, views rotas, inconsistencia técnica
    action_design  — drift ≥3 en 1 ciudad → revisión humana recomendada
    action_safety  — drift ≥3 en 2+ ciudades → inconsistencia grave (sin acción trading)

Exit codes:
    0 — siempre para report informativo (incluyendo schema_missing / empty)
    1 — solo error de argumentos CLI
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _check_view_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='view' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _determine_status(
    *,
    n_records: int,
    n_resolved: int,
    calibration_global: float | None,
    drift_cities: list,
    view_vdt_ok: bool,
) -> str:
    if not view_vdt_ok and n_records > 0:
        return "watch_tech"
    if n_records == 0:
        return "empty"
    if len(drift_cities) >= 2:
        return "action_safety"
    if drift_cities:
        return "action_design"
    if calibration_global is not None and n_resolved >= 10 and calibration_global < 0.5:
        return "watch"
    return "no_action"


def generate_report(db_path: str) -> dict:
    """
    Lee la DB indicada y genera el reporte de truth pipeline.

    No crashea si la DB no existe o las tablas no existen.
    Siempre devuelve un dict con status y detalles.
    """
    report_ts = _now_utc()

    if not Path(db_path).exists():
        return {
            "status": "watch_tech",
            "status_detail": "db_not_found",
            "db_path": db_path,
            "report_ts_utc": report_ts,
            "error": f"DB not found: {db_path}",
        }

    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError as exc:
        return {
            "status": "watch_tech",
            "status_detail": "db_inaccessible",
            "db_path": db_path,
            "report_ts_utc": report_ts,
            "error": str(exc),
        }

    try:
        truth_records_exists = _check_table_exists(conn, "truth_records")
        truth_revisions_exists = _check_table_exists(conn, "truth_revisions")
        view_ftj = _check_view_exists(conn, "forecast_truth_join")
        view_vdt = _check_view_exists(conn, "v_decision_truth")

        if not truth_records_exists:
            conn.close()
            return {
                "status": "schema_missing",
                "db_path": db_path,
                "report_ts_utc": report_ts,
                "truth_records_exists": False,
                "truth_revisions_exists": truth_revisions_exists,
                "view_forecast_truth_join": view_ftj,
                "view_v_decision_truth": view_vdt,
                "message": "truth_records table not found — schema v2 not applied.",
            }

        n_records = conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0]

        n_revisions = 0
        if truth_revisions_exists:
            n_revisions = conn.execute("SELECT COUNT(*) FROM truth_revisions").fetchone()[0]

        if n_records == 0:
            conn.close()
            return {
                "status": "empty",
                "db_path": db_path,
                "report_ts_utc": report_ts,
                "truth_records": 0,
                "truth_revisions": n_revisions,
                "view_forecast_truth_join": view_ftj,
                "view_v_decision_truth": view_vdt,
                "message": "Schema v2 applied but no truth_records yet.",
            }

        # Coverage by city
        city_rows = conn.execute(
            """
            SELECT city,
                   COUNT(*) as n_total,
                   SUM(CASE WHEN resolution_outcome IN ('YES','NO') THEN 1 ELSE 0 END) as n_resolved,
                   SUM(CASE WHEN resolution_outcome = 'UNKNOWN' THEN 1 ELSE 0 END) as n_unknown,
                   SUM(CASE WHEN observed_high_c IS NOT NULL THEN 1 ELSE 0 END) as n_with_observed,
                   MIN(snapshot_ts_utc) as first_ts,
                   MAX(snapshot_ts_utc) as last_ts
            FROM truth_records
            GROUP BY city
            ORDER BY n_total DESC
            """
        ).fetchall()

        city_coverage = [
            {
                "city": r["city"],
                "n_total": r["n_total"],
                "n_resolved": r["n_resolved"],
                "n_unknown": r["n_unknown"],
                "n_with_observed": r["n_with_observed"],
                "first_ts": r["first_ts"],
                "last_ts": r["last_ts"],
            }
            for r in city_rows
        ]

        # Outcome breakdown
        outcome_rows = conn.execute(
            "SELECT resolution_outcome, COUNT(*) as n FROM truth_records GROUP BY resolution_outcome"
        ).fetchall()
        outcomes = {r["resolution_outcome"]: r["n"] for r in outcome_rows}
        n_resolved = outcomes.get("YES", 0) + outcomes.get("NO", 0)
        n_void = outcomes.get("VOID", 0)
        n_unknown = outcomes.get("UNKNOWN", 0)

        # Freshness
        last_update = conn.execute(
            "SELECT MAX(snapshot_ts_utc) FROM truth_records"
        ).fetchone()[0]

        n_missing_obs = conn.execute(
            "SELECT COUNT(*) FROM truth_records WHERE observed_high_c IS NULL"
        ).fetchone()[0]

        # Calibration from v_decision_truth view
        calibration_global = None
        calibration_by_city: list[dict] = []
        view_vdt_ok = view_vdt
        if view_vdt:
            try:
                cal_row = conn.execute(
                    """
                    SELECT COUNT(*) as n_with_forecast,
                           SUM(CASE WHEN forecast_correct = 1 THEN 1 ELSE 0 END) as n_correct
                    FROM v_decision_truth
                    WHERE forecast_correct IS NOT NULL
                    """
                ).fetchone()
                if cal_row and cal_row["n_with_forecast"] > 0:
                    calibration_global = round(
                        cal_row["n_correct"] / cal_row["n_with_forecast"], 3
                    )

                cal_city_rows = conn.execute(
                    """
                    SELECT city,
                           COUNT(*) as n,
                           SUM(CASE WHEN forecast_correct = 1 THEN 1 ELSE 0 END) as n_ok
                    FROM v_decision_truth
                    WHERE forecast_correct IS NOT NULL
                    GROUP BY city
                    ORDER BY n DESC
                    """
                ).fetchall()
                calibration_by_city = [
                    {
                        "city": r["city"],
                        "n": r["n"],
                        "n_ok": r["n_ok"],
                        "calibration": round(r["n_ok"] / r["n"], 3) if r["n"] > 0 else None,
                    }
                    for r in cal_city_rows
                ]
            except sqlite3.OperationalError:
                view_vdt_ok = False

        # Drift check: ≥3 wrong forecasts for same city/condition (exact)
        drift_cities: list[dict] = []
        try:
            drift_rows = conn.execute(
                """
                SELECT city, condition, COUNT(*) as n_wrong
                FROM (
                    SELECT city, condition, resolution_outcome,
                           forecast_high_c, threshold_c,
                           CASE
                               WHEN condition = 'exact'
                                AND threshold_c IS NOT NULL
                                AND forecast_high_c IS NOT NULL
                                AND resolution_outcome IN ('YES','NO')
                                AND ((forecast_high_c >= threshold_c AND resolution_outcome = 'NO')
                                  OR (forecast_high_c < threshold_c AND resolution_outcome = 'YES'))
                               THEN 1 ELSE 0
                           END as was_wrong
                    FROM truth_records
                    WHERE resolution_outcome IN ('YES', 'NO')
                      AND condition = 'exact'
                )
                WHERE was_wrong = 1
                GROUP BY city, condition
                HAVING n_wrong >= 3
                """
            ).fetchall()
            drift_cities = [
                {"city": r["city"], "condition": r["condition"], "n_wrong": r["n_wrong"]}
                for r in drift_rows
            ]
        except sqlite3.OperationalError:
            pass

        conn.close()

        status = _determine_status(
            n_records=n_records,
            n_resolved=n_resolved,
            calibration_global=calibration_global,
            drift_cities=drift_cities,
            view_vdt_ok=view_vdt_ok,
        )

        return {
            "status": status,
            "db_path": db_path,
            "report_ts_utc": report_ts,
            "last_update_ts": last_update,
            "truth_records": n_records,
            "truth_revisions": n_revisions,
            "n_resolved": n_resolved,
            "n_void": n_void,
            "n_unknown": n_unknown,
            "n_missing_observed": n_missing_obs,
            "calibration_global": calibration_global,
            "calibration_by_city": calibration_by_city,
            "city_coverage": city_coverage,
            "drift_alert_cities": drift_cities,
            "views": {
                "forecast_truth_join": view_ftj,
                "v_decision_truth": view_vdt_ok,
            },
        }

    except sqlite3.OperationalError as exc:
        try:
            conn.close()
        except Exception:
            pass
        return {
            "status": "watch_tech",
            "status_detail": "db_read_error",
            "db_path": db_path,
            "report_ts_utc": report_ts,
            "error": str(exc),
        }


def _print_human(report: dict) -> None:
    status = report.get("status", "unknown")
    print(f"\nTruth Pipeline — Reporte de estado")
    print(f"  DB:       {report.get('db_path', '-')}")
    print(f"  Timestamp:{report.get('report_ts_utc', '-')}")
    print(f"  Estado:   {status.upper()}")

    if status in ("schema_missing", "watch_tech"):
        print(f"  Detalle:  {report.get('message') or report.get('error', '-')}")
        return

    if status == "empty":
        print(f"  Detalle:  {report.get('message', 'Sin registros.')}")
        return

    print(f"  Registros:    {report.get('truth_records', 0)}")
    print(f"  Revisiones:   {report.get('truth_revisions', 0)}")
    print(f"  Resueltos:    {report.get('n_resolved', 0)}")
    print(f"  Desconocidos: {report.get('n_unknown', 0)}")
    print(f"  Sin observado:{report.get('n_missing_observed', 0)}")
    cal = report.get("calibration_global")
    print(f"  Calibración:  {f'{cal*100:.1f}%' if cal is not None else 'N/A'}")
    print(f"  Última act.:  {report.get('last_update_ts', '-')}")

    city_cov = report.get("city_coverage", [])
    if city_cov:
        print("\n  Cobertura por ciudad:")
        for c in city_cov:
            print(
                f"    {c['city']:<16} total={c['n_total']}  "
                f"resueltos={c['n_resolved']}  desconocidos={c['n_unknown']}"
            )

    drift = report.get("drift_alert_cities", [])
    if drift:
        print("\n  DRIFT DETECTADO:")
        for d in drift:
            print(f"    {d['city']} ({d['condition']}): {d['n_wrong']} incorrectos")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Truth Pipeline reporter — estadísticas de truth_records"
    )
    parser.add_argument("--db", required=True, help="Ruta a polymarket.db")
    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    args = parser.parse_args()

    report = generate_report(args.db)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_human(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
