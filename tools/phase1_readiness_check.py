#!/usr/bin/env python3
"""
tools/phase1_readiness_check.py — Fase 0.5: Health del SQLite Recorder.

Verifica que el recorder está acumulando datos correctamente y calcula
cuándo la base tiene suficiente evidencia para diseñar Fase 1 (Truth Pipeline).

Sin dependencias externas. No importa bot.py ni ningún módulo del proyecto.

Uso:
    python tools/phase1_readiness_check.py
    python tools/phase1_readiness_check.py --db /app/data/polymarket.db
    python tools/phase1_readiness_check.py --min-days 7 --min-cycles 21
    python tools/phase1_readiness_check.py --json

Exit codes:
    0 — DB sana y readiness para Fase 1 cumplida
    1 — DB sana pero evidencia insuficiente todavía (esperar más datos)
    2 — DB no existe, no accesible o recorder no activado
    3 — DB existe pero tiene problemas (tablas faltantes, posible corrupción)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Defaults (sobrescribibles por args)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_DB_PATHS = [
    "data/polymarket.db",
    "/app/data/polymarket.db",
]
DEFAULT_MIN_DAYS = 7
DEFAULT_MIN_CYCLES = 21          # 7 días × 3 ciclos/día
DEFAULT_MIN_MARKET_ROWS = 1      # al menos algún dato de ciudad
DEFAULT_MAX_LAST_WRITE_HOURS = 30  # si el último write es > 30h, alerta
EXPECTED_CYCLES_PER_DAY = 3      # según schedule 8,16,23 UTC

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _find_db(db_arg: str | None) -> Path | None:
    if db_arg:
        p = Path(db_arg)
        return p if p.exists() else None
    for candidate in DEFAULT_DB_PATHS:
        p = Path(candidate)
        if p.exists():
            return p
    return None


def _open_db(db_path: Path) -> sqlite3.Connection | None:
    try:
        con = sqlite3.connect(db_path, timeout=5)
        con.row_factory = sqlite3.Row
        return con
    except sqlite3.Error:
        return None


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f+00:00", "%Y-%m-%dT%H:%M:%S+00:00",
                "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(ts[:26], fmt[:len(ts[:26])])
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _fmt_delta(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)}min"
    if hours < 48:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f} días"


# ──────────────────────────────────────────────────────────────────────────────
# Checks principales
# ──────────────────────────────────────────────────────────────────────────────

def check_tables(con: sqlite3.Connection) -> dict:
    required = ["cycle_events", "market_snapshots", "forecast_snapshots"]
    present = {t: _table_exists(con, t) for t in required}
    schema_ok = _table_exists(con, "schema_version")
    schema_version = None
    if schema_ok:
        row = con.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
        schema_version = row[0] if row else None
    return {
        "tables_present": present,
        "all_required_tables_ok": all(present.values()),
        "schema_version_table": schema_ok,
        "schema_version": schema_version,
    }


def check_cycle_events(con: sqlite3.Connection) -> dict:
    total = con.execute("SELECT COUNT(*) FROM cycle_events").fetchone()[0]
    if total == 0:
        return {"total": 0, "first_ts": None, "last_ts": None, "days_span": 0,
                "distinct_days": 0, "mode_counts": {}, "version_counts": {},
                "gaps": [], "avg_hours_between": None}

    row = con.execute(
        "SELECT MIN(ts_utc), MAX(ts_utc) FROM cycle_events"
    ).fetchone()
    first_ts_str, last_ts_str = row[0], row[1]
    first_ts = _parse_ts(first_ts_str)
    last_ts = _parse_ts(last_ts_str)

    days_span = 0.0
    if first_ts and last_ts:
        days_span = (last_ts - first_ts).total_seconds() / 86400

    # Días calendario con al menos un ciclo
    distinct_days = con.execute(
        "SELECT COUNT(DISTINCT substr(ts_utc, 1, 10)) FROM cycle_events"
    ).fetchone()[0]

    # Conteos por mode (REAL vs DRY_RUN)
    mode_rows = con.execute(
        "SELECT mode, COUNT(*) FROM cycle_events GROUP BY mode"
    ).fetchall()
    mode_counts = {r[0] or "unknown": r[1] for r in mode_rows}

    # Conteos por bot_version
    ver_rows = con.execute(
        "SELECT bot_version, COUNT(*) FROM cycle_events GROUP BY bot_version ORDER BY COUNT(*) DESC LIMIT 5"
    ).fetchall()
    version_counts = {r[0] or "unknown": r[1] for r in ver_rows}

    # Detección de gaps: ciclos consecutivos con gap > 18h (más de 1 ciclo perdido)
    ts_rows = con.execute(
        "SELECT ts_utc FROM cycle_events ORDER BY ts_utc ASC"
    ).fetchall()
    timestamps = [_parse_ts(r[0]) for r in ts_rows if r[0]]
    timestamps = [t for t in timestamps if t is not None]

    gaps = []
    for i in range(1, len(timestamps)):
        delta_h = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600
        if delta_h > 18:
            gaps.append({
                "from": timestamps[i - 1].isoformat(),
                "to": timestamps[i].isoformat(),
                "gap_hours": round(delta_h, 1),
            })

    avg_hours = None
    if len(timestamps) >= 2:
        total_span_h = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        avg_hours = round(total_span_h / (len(timestamps) - 1), 1)

    return {
        "total": total,
        "first_ts": first_ts_str,
        "last_ts": last_ts_str,
        "days_span": round(days_span, 1),
        "distinct_days": distinct_days,
        "mode_counts": mode_counts,
        "version_counts": version_counts,
        "gaps": gaps,
        "avg_hours_between": avg_hours,
    }


def check_market_snapshots(con: sqlite3.Connection) -> dict:
    total = con.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
    if total == 0:
        return {"total": 0, "cities": [], "city_counts": {}, "date_range": None}

    city_rows = con.execute(
        "SELECT city, COUNT(*) as n FROM market_snapshots GROUP BY city ORDER BY n DESC"
    ).fetchall()
    city_counts = {r[0]: r[1] for r in city_rows}

    row = con.execute(
        "SELECT MIN(date_iso), MAX(date_iso) FROM market_snapshots"
    ).fetchone()
    date_range = {"from": row[0], "to": row[1]} if row[0] else None

    return {
        "total": total,
        "cities": list(city_counts.keys()),
        "city_counts": city_counts,
        "date_range": date_range,
    }


def check_forecast_snapshots(con: sqlite3.Connection) -> dict:
    total = con.execute("SELECT COUNT(*) FROM forecast_snapshots").fetchone()[0]
    if total == 0:
        return {"total": 0, "cities": [], "city_counts": {}}

    city_rows = con.execute(
        "SELECT city, COUNT(*) as n FROM forecast_snapshots GROUP BY city ORDER BY n DESC"
    ).fetchall()
    city_counts = {r[0]: r[1] for r in city_rows}

    return {
        "total": total,
        "cities": list(city_counts.keys()),
        "city_counts": city_counts,
    }


def check_last_write_freshness(cycle_info: dict, max_hours: float) -> dict:
    last_ts_str = cycle_info.get("last_ts")
    last_ts = _parse_ts(last_ts_str) if last_ts_str else None
    if not last_ts:
        return {"last_ts": None, "hours_ago": None, "is_stale": True,
                "stale_threshold_hours": max_hours}

    now = datetime.now(timezone.utc)
    hours_ago = (now - last_ts).total_seconds() / 3600
    return {
        "last_ts": last_ts_str,
        "hours_ago": round(hours_ago, 1),
        "is_stale": hours_ago > max_hours,
        "stale_threshold_hours": max_hours,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Evaluación de readiness para Fase 1
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_readiness(
    cycle_info: dict,
    market_info: dict,
    forecast_info: dict,
    freshness: dict,
    min_days: int,
    min_cycles: int,
) -> dict:
    criteria = {}

    criteria["enough_days"] = {
        "ok": cycle_info["days_span"] >= min_days,
        "value": cycle_info["days_span"],
        "required": min_days,
        "label": f"{cycle_info['days_span']:.1f} días ≥ {min_days} requeridos",
    }
    criteria["enough_cycles"] = {
        "ok": cycle_info["total"] >= min_cycles,
        "value": cycle_info["total"],
        "required": min_cycles,
        "label": f"{cycle_info['total']} ciclos ≥ {min_cycles} requeridos",
    }
    criteria["has_market_data"] = {
        "ok": market_info["total"] > 0,
        "value": market_info["total"],
        "required": 1,
        "label": f"{market_info['total']} filas en market_snapshots",
    }
    criteria["has_forecast_data"] = {
        "ok": forecast_info["total"] > 0,
        "value": forecast_info["total"],
        "required": 1,
        "label": f"{forecast_info['total']} filas en forecast_snapshots",
    }
    criteria["recorder_fresh"] = {
        "ok": not freshness["is_stale"],
        "value": freshness.get("hours_ago"),
        "required": freshness["stale_threshold_hours"],
        "label": (
            f"último write hace {_fmt_delta(freshness['hours_ago'])}"
            if freshness.get("hours_ago") is not None else "sin datos"
        ),
    }
    criteria["no_large_gaps"] = {
        "ok": len(cycle_info.get("gaps", [])) == 0,
        "value": len(cycle_info.get("gaps", [])),
        "required": 0,
        "label": f"{len(cycle_info.get('gaps', []))} gaps grandes (>18h)",
    }

    all_ok = all(c["ok"] for c in criteria.values())

    # Estimación de cuántos días faltan
    days_remaining = max(0, min_days - cycle_info["days_span"])
    cycles_remaining = max(0, min_cycles - cycle_info["total"])
    days_by_cycles = cycles_remaining / EXPECTED_CYCLES_PER_DAY if cycles_remaining > 0 else 0
    days_needed = max(days_remaining, days_by_cycles)

    eta_date = None
    if days_needed > 0 and cycle_info.get("last_ts"):
        last_ts = _parse_ts(cycle_info["last_ts"])
        if last_ts:
            eta_date = (last_ts + timedelta(days=days_needed)).strftime("%Y-%m-%d")

    return {
        "ready": all_ok,
        "criteria": criteria,
        "days_remaining": round(days_remaining, 1),
        "cycles_remaining": cycles_remaining,
        "eta_date": eta_date,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Informe en consola
# ──────────────────────────────────────────────────────────────────────────────

def print_report(
    db_path: Path,
    tables: dict,
    cycle_info: dict,
    market_info: dict,
    forecast_info: dict,
    freshness: dict,
    readiness: dict,
    exit_code: int,
) -> None:
    W = 60
    sep = "─" * W
    print(f"\n{'═' * W}")
    print(f"  SQLite Recorder — Health & Phase 1 Readiness")
    print(f"  DB: {db_path}")
    print(f"  Hora UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * W}")

    # Tablas
    print(f"\n[TABLAS]")
    for table, ok in tables["tables_present"].items():
        mark = "[OK]" if ok else "[--]"
        print(f"  {mark} {table}")
    sv = tables.get("schema_version")
    print(f"  Schema version: {sv if sv else 'n/d'}")

    # Ciclos
    print(f"\n[CICLOS]  {cycle_info['total']} registros en cycle_events")
    if cycle_info["total"] > 0:
        print(f"  Primer ciclo : {cycle_info['first_ts'] or 'n/d'}")
        print(f"  Último ciclo : {cycle_info['last_ts'] or 'n/d'}")
        print(f"  Rango        : {cycle_info['days_span']:.1f} días")
        print(f"  Días distintos: {cycle_info['distinct_days']}")
        if cycle_info.get("avg_hours_between"):
            print(f"  Intervalo medio: {cycle_info['avg_hours_between']}h entre ciclos")
        if cycle_info.get("mode_counts"):
            modes = ", ".join(f"{k}={v}" for k, v in cycle_info["mode_counts"].items())
            print(f"  Modos        : {modes}")
        if cycle_info.get("gaps"):
            print(f"  [!!] {len(cycle_info['gaps'])} gaps grandes detectados:")
            for g in cycle_info["gaps"][:5]:
                print(f"       {g['from']} → {g['to']}  ({g['gap_hours']}h)")
        else:
            print(f"  Gaps (>18h)  : ninguno")

    # Market snapshots
    print(f"\n[MARKET SNAPSHOTS]  {market_info['total']} filas")
    if market_info["city_counts"]:
        for city, n in list(market_info["city_counts"].items())[:8]:
            print(f"  {city:<20} {n:>4} filas")
        if len(market_info["city_counts"]) > 8:
            print(f"  ... y {len(market_info['city_counts']) - 8} ciudades más")
    if market_info.get("date_range"):
        dr = market_info["date_range"]
        print(f"  Fechas target : {dr['from']} → {dr['to']}")

    # Forecast snapshots
    print(f"\n[FORECAST SNAPSHOTS]  {forecast_info['total']} filas")
    if forecast_info["city_counts"]:
        for city, n in list(forecast_info["city_counts"].items())[:5]:
            print(f"  {city:<20} {n:>4} filas")

    # Freshness
    print(f"\n[FRESHNESS]")
    h = freshness.get("hours_ago")
    if h is not None:
        stale_mark = "[!!]" if freshness["is_stale"] else "[OK]"
        print(f"  {stale_mark} Último write hace {_fmt_delta(h)}")
        print(f"       Umbral de alerta: {freshness['stale_threshold_hours']}h")
    else:
        print(f"  [??] Sin datos de timestamp")

    # Readiness para Fase 1
    print(f"\n[READINESS FASE 1]")
    print(sep)
    all_ok = readiness["ready"]
    for key, c in readiness["criteria"].items():
        mark = "[OK]" if c["ok"] else "[ ]"
        print(f"  {mark} {c['label']}")
    print(sep)

    if all_ok:
        print(f"  VEREDICTO: LISTO para diseñar Fase 1")
    else:
        eta = readiness.get("eta_date")
        rem_days = readiness.get("days_remaining", 0)
        rem_cycles = readiness.get("cycles_remaining", 0)
        print(f"  VEREDICTO: Insuficiente evidencia todavía")
        if rem_days > 0 or rem_cycles > 0:
            print(f"  Faltan aprox: {rem_days:.1f} días más / {rem_cycles} ciclos más")
        if eta:
            print(f"  ETA estimada : {eta} (si el recorder sigue activo)")
        print(f"  Acción       : esperar y volver a correr este script")

    print(f"\n{'═' * W}")
    codes = {0: "LISTO (exit 0)", 1: "ESPERANDO DATOS (exit 1)",
             2: "DB NO DISPONIBLE (exit 2)", 3: "PROBLEMA EN DB (exit 3)"}
    print(f"  Exit code: {exit_code} — {codes.get(exit_code, '?')}")
    print(f"{'═' * W}\n")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    db_path = _find_db(args.db)

    if db_path is None:
        if args.json:
            print(json.dumps({"status": "db_not_found", "exit_code": 2}))
        else:
            print("[RECORDER] DB no encontrada.")
            checked = [args.db] if args.db else DEFAULT_DB_PATHS
            for p in checked:
                print(f"  Buscado: {p}")
            print("  ¿Está SQLITE_RECORDER_ENABLED=1 en Railway y ha corrido al menos 1 ciclo?")
        return 2

    con = _open_db(db_path)
    if con is None:
        if args.json:
            print(json.dumps({"status": "db_open_error", "exit_code": 2, "db": str(db_path)}))
        else:
            print(f"[RECORDER] No se puede abrir {db_path}")
        return 2

    try:
        tables = check_tables(con)
    except sqlite3.Error as e:
        if args.json:
            print(json.dumps({"status": "db_error", "error": str(e), "exit_code": 3}))
        else:
            print(f"[RECORDER] Error leyendo tablas: {e}")
        con.close()
        return 3

    if not tables["all_required_tables_ok"]:
        missing = [t for t, ok in tables["tables_present"].items() if not ok]
        if args.json:
            print(json.dumps({"status": "missing_tables", "missing": missing, "exit_code": 3}))
        else:
            print(f"[RECORDER] Tablas faltantes: {missing}")
            print("  ¿El schema se inicializó correctamente? Verificar sqlite_recorder.py._init_schema()")
        con.close()
        return 3

    cycle_info = check_cycle_events(con)
    market_info = check_market_snapshots(con)
    forecast_info = check_forecast_snapshots(con)
    freshness = check_last_write_freshness(cycle_info, args.max_stale_hours)
    readiness = evaluate_readiness(
        cycle_info, market_info, forecast_info, freshness,
        args.min_days, args.min_cycles,
    )
    con.close()

    if args.json:
        output = {
            "db": str(db_path),
            "tables": tables,
            "cycle_events": cycle_info,
            "market_snapshots": market_info,
            "forecast_snapshots": forecast_info,
            "freshness": freshness,
            "readiness": readiness,
            "exit_code": 0 if readiness["ready"] else 1,
        }
        print(json.dumps(output, indent=2, default=str))
        return 0 if readiness["ready"] else 1

    exit_code = 0 if readiness["ready"] else 1
    print_report(db_path, tables, cycle_info, market_info, forecast_info,
                 freshness, readiness, exit_code)
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifica la salud del SQLite Recorder y la readiness para Fase 1."
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Ruta a polymarket.db (default: busca en data/ y /app/data/)",
    )
    parser.add_argument(
        "--min-days",
        type=int,
        default=DEFAULT_MIN_DAYS,
        dest="min_days",
        help=f"Días mínimos de datos requeridos (default: {DEFAULT_MIN_DAYS})",
    )
    parser.add_argument(
        "--min-cycles",
        type=int,
        default=DEFAULT_MIN_CYCLES,
        dest="min_cycles",
        help=f"Ciclos mínimos requeridos (default: {DEFAULT_MIN_CYCLES})",
    )
    parser.add_argument(
        "--max-stale-hours",
        type=float,
        default=DEFAULT_MAX_LAST_WRITE_HOURS,
        dest="max_stale_hours",
        help=f"Horas máximas sin write antes de marcar como stale (default: {DEFAULT_MAX_LAST_WRITE_HOURS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output en JSON (para integración con otros scripts)",
    )
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
