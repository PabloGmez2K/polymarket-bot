"""
Bankroll Bottleneck Readiness Score — ¿cuán cerca estamos de que el bankroll sea el cuello?

Score 0-100%. Cuando supera ~75%, el sistema está validado y el bankroll es la limitación real.
Dimensiones:
  D1 WR Confidence    (30%) — win rate live con confianza estadística
  D2 PnL Trajectory   (25%) — PnL positivo sostenido en 30d+60d
  D3 Edge Density     (20%) — edges encontrados por ciclo (consistencia)
  D4 Size Pressure    (15%) — kelly_too_low como señal de que bankroll limita
  D5 System Stability (10%) — versión estable sin hotfixes críticos
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data" / "runtime_import"
STATE_FILE = REPO_ROOT / "data" / "bankroll_readiness_state.json"

THRESHOLDS = {
    "add_capital": 75,
    "getting_close": 60,
    "improving": 40,
}

LABELS = {
    "add_capital":   "🏦 BANKROLL ES EL CUELLO — considera aumentar capital",
    "getting_close": "📈 SISTEMA MADURANDO — sigue validando",
    "improving":     "🔧 EN PROGRESO — cuello sigue siendo el sistema",
    "early":         "🌱 ETAPA TEMPRANA — focus en calidad de señales",
}


def load_json(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding) as f:
        return json.load(f)


def load_jsonl(path, encoding="utf-8-sig"):
    rows = []
    with open(path, encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ── D1: WR Confidence ──────────────────────────────────────────────────────────

def compute_wr_confidence(trade_lifecycle, window_days=60):
    """
    WR sobre trades reales cerrados en la ventana. Excluye legacy_unresolved (phantom).
    Score = n_factor × wr_factor, cada uno 0-1.
    - n_factor: min(n/20, 1.0) — necesitas n≥20 para factor pleno
    - wr_factor: (WR - 0.45) / 0.25 clamped [0,1] — 0 en WR=45%, 1 en WR=70%+
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    recs = trade_lifecycle.get("records", [])

    real = []
    for r in recs:
        if r.get("status") != "closed":
            continue
        if r.get("total_amount", 0) <= 0:
            continue
        cc = r.get("close_context", {})
        subtype = cc.get("close_subtype", "")
        if subtype == "legacy_unresolved":
            continue
        pnl = cc.get("pnl_cash")
        if pnl is None:
            continue
        closed_at = parse_dt(r.get("closed_at", ""))
        if not closed_at or closed_at < cutoff:
            continue
        real.append({"pnl": pnl, "city": r.get("city", "?")})

    n = len(real)
    if n == 0:
        return 0.0, {"n": 0, "wr": 0.0, "n_factor": 0.0, "wr_factor": 0.0}

    wins = sum(1 for r in real if r["pnl"] > 0)
    wr = wins / n
    n_factor = min(n / 20.0, 1.0)
    wr_factor = max((wr - 0.45) / 0.25, 0.0)
    wr_factor = min(wr_factor, 1.0)
    score = n_factor * wr_factor * 100

    return score, {"n": n, "wr": round(wr * 100, 1), "wins": wins,
                   "n_factor": round(n_factor, 2), "wr_factor": round(wr_factor, 2)}


# ── D2: PnL Trajectory ─────────────────────────────────────────────────────────

def compute_pnl_trajectory(trade_lifecycle):
    """
    30d PnL positivo: 60pts. 60d PnL positivo: 40pts. Total max 100.
    """
    now = datetime.now(timezone.utc)
    recs = trade_lifecycle.get("records", [])

    pnl_by_window = {}
    for days in (30, 60):
        cutoff = now - timedelta(days=days)
        total = 0.0
        for r in recs:
            if r.get("status") != "closed" or r.get("total_amount", 0) <= 0:
                continue
            cc = r.get("close_context", {})
            if cc.get("close_subtype") == "legacy_unresolved":
                continue
            pnl = cc.get("pnl_cash")
            if pnl is None:
                continue
            closed_at = parse_dt(r.get("closed_at", ""))
            if closed_at and closed_at >= cutoff:
                total += pnl
        pnl_by_window[days] = round(total, 2)

    score = 0.0
    if pnl_by_window[30] > 0:
        score += 60
    if pnl_by_window[60] > 0:
        score += 40

    return score, {"pnl_30d": pnl_by_window[30], "pnl_60d": pnl_by_window[60]}


# ── D3: Edge Density ───────────────────────────────────────────────────────────

def compute_edge_density(cycles_history, window_days=14):
    """
    Avg edges encontrados por ciclo en los últimos N días.
    Target: 1.0 edge/ciclo. Score = min(avg/1.0, 1.0) × 100.
    También penaliza alta varianza (inconsistencia).
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    recent = []
    for c in cycles_history:
        ts = parse_dt(c.get("timestamp_utc", ""))
        if ts and ts >= cutoff:
            recent.append(c)

    if not recent:
        return 0.0, {"n_cycles": 0, "avg_edges": 0.0}

    edges = [c.get("scan", {}).get("with_edge", 0) for c in recent]
    avg = sum(edges) / len(edges)
    score = min(avg / 1.0, 1.0) * 100

    return score, {"n_cycles": len(recent), "avg_edges": round(avg, 2),
                   "total_edges": sum(edges)}


# ── D4: Size Pressure ──────────────────────────────────────────────────────────

def compute_size_pressure(skip_log, window_days=14):
    """
    kelly_too_low skips como fracción de todos los skips con edge evaluado.
    Señal: el bot quiere apostar pero el bankroll lo limita.
    Score = min(rate / 0.10, 1.0) × 100 — lleno si 10%+ de oportunidades bloqueadas por kelly.
    También cuenta buy_min_size si aparece en extras.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    size_blocked = 0
    edge_evaluated = 0

    for s in skip_log:
        ts = parse_dt(s.get("ts_utc", ""))
        if not ts or ts < cutoff:
            continue
        reason = s.get("skip_reason", "")
        # Oportunidades donde edge fue evaluado (below_min_edge, kelly_too_low, existing_position)
        if reason in ("kelly_too_low", "below_min_edge", "existing_position",
                      "sl_city_cooldown", "liquidity_low", "buy_min_size"):
            edge_evaluated += 1
            if reason in ("kelly_too_low", "buy_min_size"):
                size_blocked += 1

    if edge_evaluated == 0:
        return 0.0, {"size_blocked": 0, "edge_evaluated": 0, "rate": 0.0}

    rate = size_blocked / edge_evaluated
    score = min(rate / 0.10, 1.0) * 100

    return score, {"size_blocked": size_blocked, "edge_evaluated": edge_evaluated,
                   "rate": round(rate * 100, 1)}


# ── D5: System Stability ───────────────────────────────────────────────────────

def compute_system_stability(cycles_history, window_days=7):
    """
    Versión consistente en los últimos 7 días = sin hotfixes críticos recientes.
    Score = % de ciclos en la versión dominante, con suavizado para desarrollo activo.
    Ventana corta (7d) para no penalizar el desarrollo normal entre semanas.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    recent = []
    for c in cycles_history:
        ts = parse_dt(c.get("timestamp_utc", ""))
        if ts and ts >= cutoff:
            recent.append(c)

    if not recent:
        return 50.0, {"n_cycles": 0, "unique_versions": 0,
                      "dominant_version": "?", "consistency_pct": 0.0}

    versions = [c.get("version", "?") for c in recent]
    from collections import Counter
    counts = Counter(versions)
    most_common_version, most_common_count = counts.most_common(1)[0]
    consistency = most_common_count / len(recent)
    unique_versions = len(counts)
    # Penalización suave: -5pp por cada versión extra más allá de 3
    penalty = max(0, (unique_versions - 3) * 0.05)
    score = max(0.0, min(consistency - penalty, 1.0)) * 100

    return score, {"n_cycles": len(recent), "unique_versions": unique_versions,
                   "dominant_version": most_common_version,
                   "consistency_pct": round(consistency * 100, 1)}


# ── Composite Score ────────────────────────────────────────────────────────────

WEIGHTS = {
    "wr_confidence":    0.30,
    "pnl_trajectory":  0.25,
    "edge_density":     0.20,
    "size_pressure":    0.15,
    "system_stability": 0.10,
}


def compute_composite(scores):
    return round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS), 1)


def status_label(score):
    if score >= THRESHOLDS["add_capital"]:
        return "add_capital"
    if score >= THRESHOLDS["getting_close"]:
        return "getting_close"
    if score >= THRESHOLDS["improving"]:
        return "improving"
    return "early"


# ── Trend ──────────────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        try:
            return load_json(STATE_FILE)
        except Exception:
            pass
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def trend_arrow(current, previous):
    if previous is None:
        return "→"
    delta = current - previous
    if delta >= 3:
        return f"↑ +{delta:.1f}pp"
    if delta <= -3:
        return f"↓ {delta:.1f}pp"
    return f"→ {delta:+.1f}pp"


# ── Report ─────────────────────────────────────────────────────────────────────

def build_report(composite, dim_scores, dim_details, prev_score, dry_run=False):
    status = status_label(composite)
    arrow = trend_arrow(composite, prev_score)
    bar_filled = int(composite / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    lines = [
        f"📊 BANKROLL READINESS SCORE",
        f"",
        f"  [{bar}] {composite:.1f}% {arrow}",
        f"  {LABELS[status]}",
        f"",
        f"DIMENSIONES:",
        f"  D1 WR Confidence    {dim_scores['wr_confidence']:5.1f}/100  (peso 30%)",
        f"     WR={dim_details['wr_confidence']['wr']}% n={dim_details['wr_confidence']['n']} "
        f"[n_factor={dim_details['wr_confidence']['n_factor']} wr_factor={dim_details['wr_confidence']['wr_factor']}]",
        f"  D2 PnL Trajectory   {dim_scores['pnl_trajectory']:5.1f}/100  (peso 25%)",
        f"     PnL 30d=${dim_details['pnl_trajectory']['pnl_30d']:+.2f}  "
        f"PnL 60d=${dim_details['pnl_trajectory']['pnl_60d']:+.2f}",
        f"  D3 Edge Density     {dim_scores['edge_density']:5.1f}/100  (peso 20%)",
        f"     {dim_details['edge_density']['avg_edges']:.2f} edges/ciclo  "
        f"({dim_details['edge_density']['total_edges']} edges en {dim_details['edge_density']['n_cycles']} ciclos, 14d)",
        f"  D4 Size Pressure    {dim_scores['size_pressure']:5.1f}/100  (peso 15%)",
        f"     kelly_too_low/min_size={dim_details['size_pressure']['size_blocked']} "
        f"de {dim_details['size_pressure']['edge_evaluated']} oportunidades con edge ({dim_details['size_pressure']['rate']}%)",
        f"  D5 System Stability {dim_scores['system_stability']:5.1f}/100  (peso 10%)",
        f"     {dim_details['system_stability']['unique_versions']} versiones en 14d, "
        f"dominante={dim_details['system_stability']['dominant_version']} "
        f"({dim_details['system_stability']['consistency_pct']}% ciclos)",
        f"",
    ]

    if status == "add_capital":
        lines += [
            f"✅ ACCIÓN: El sistema está validado. El bankroll es el cuello.",
            f"   → Considera subir de $25 a $50.",
        ]
    elif status == "getting_close":
        lines += [
            f"⏳ ACCIÓN: Sigue validando. Faltan ~{THRESHOLDS['add_capital'] - composite:.0f}pp para el umbral.",
            f"   → Prioriza mejorar WR y mantener PnL positivo.",
        ]
    elif status == "improving":
        lines += [
            f"🔧 ACCIÓN: El cuello sigue siendo calidad del sistema, no capital.",
            f"   → Focus en WR, edge density y PnL positivo 30d.",
        ]
    else:
        lines += [
            f"🌱 ACCIÓN: Etapa temprana. Acumula n≥20 trades y WR>50%.",
        ]

    if dry_run:
        lines.append(f"\n[DRY RUN — estado no guardado]")

    return "\n".join(lines)


# ── Telegram ───────────────────────────────────────────────────────────────────

def send_telegram(msg):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"sent": False, "reason": "no_credentials"}
    import urllib.request
    payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return {"sent": True, "status": r.status}
    except Exception as e:
        return {"sent": False, "reason": str(e)}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bankroll Readiness Score")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--telegram", action="store_true", help="Enviar a Telegram")
    parser.add_argument("--dry-run", action="store_true", help="No guardar estado")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    # Load data
    trade_lifecycle = load_json(data_dir / "trade_lifecycle.json")
    cycles_history = load_jsonl(data_dir / "cycles_history.jsonl")
    skip_log = load_jsonl(data_dir / "skip_log.jsonl")

    # Compute dimensions
    s1, d1 = compute_wr_confidence(trade_lifecycle)
    s2, d2 = compute_pnl_trajectory(trade_lifecycle)
    s3, d3 = compute_edge_density(cycles_history)
    s4, d4 = compute_size_pressure(skip_log)
    s5, d5 = compute_system_stability(cycles_history)

    dim_scores = {
        "wr_confidence": s1,
        "pnl_trajectory": s2,
        "edge_density": s3,
        "size_pressure": s4,
        "system_stability": s5,
    }
    dim_details = {
        "wr_confidence": d1,
        "pnl_trajectory": d2,
        "edge_density": d3,
        "size_pressure": d4,
        "system_stability": d5,
    }

    composite = compute_composite(dim_scores)

    # Trend
    prev_state = load_state()
    prev_score = prev_state.get("composite")

    if args.json:
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "composite": composite,
            "prev_composite": prev_score,
            "status": status_label(composite),
            "dimensions": {k: {"score": dim_scores[k], "details": dim_details[k]} for k in dim_scores},
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        report = build_report(composite, dim_scores, dim_details, prev_score, args.dry_run)
        print(report)

    # Save state
    if not args.dry_run:
        new_state = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "composite": composite,
            "status": status_label(composite),
            "dimensions": {k: {"score": dim_scores[k], **dim_details[k]} for k in dim_scores},
            "history": prev_state.get("history", []) + [
                {"ts": datetime.now(timezone.utc).isoformat(), "score": composite}
            ],
        }
        save_state(new_state)

    # Telegram
    if args.telegram:
        report = build_report(composite, dim_scores, dim_details, prev_score)
        result = send_telegram(report)
        print(f"Telegram: {result}")

    return composite


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
