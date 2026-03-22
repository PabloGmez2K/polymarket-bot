"""
trader_analyzer.py v2 — Análisis profundo + señales accionables
================================================================

Pipeline:   find_traders.py → traders_db.json → trader_analyzer.py → signals.json

Cambios vs v1:
  - Solo analiza traders de traders_db.json (no hardcoded duplicados)
  - Produce signals.json que bot.py consume directamente
  - Señal = "trader X compró YES en mercado Y a precio Z"
  - Cuando bot.py encuentra edge Y un trader tracked coincide → señal confirmada
  - Más ligero: menos prints, más datos estructurados

Uso:
    python trader_analyzer.py              # análisis completo
    python trader_analyzer.py --signals    # solo generar signals.json (rápido)

Llamable desde bot.py:
    from trader_analyzer import get_trader_signals
    signals = get_trader_signals()
"""

import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
from datetime import datetime, timezone

# ============================================================
# CONFIG
# ============================================================

DATA_API  = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

DB_FILE      = "traders_db.json"
SIGNALS_FILE = "signals.json"      # señales para bot.py
HISTORY_FILE = "trader_history.json"

# Rango de precio que nos interesa
MIN_PRICE = 0.08
MAX_PRICE = 0.92


# ============================================================
# API
# ============================================================

def api_get(url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-analyzer/2.0")
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(delay)
    return None


def get_positions(address, limit=50):
    """Posiciones activas de un trader."""
    params = urllib.parse.urlencode({
        "user": address.lower(),
        "sizeThreshold": "0.1",
        "limit": limit,
        "sortBy": "CURRENT",
        "sortDirection": "DESC",
    })
    return api_get(f"{DATA_API}/positions?{params}") or []


def get_closed_positions(address, limit=100):
    """Posiciones cerradas para win rate."""
    params = urllib.parse.urlencode({
        "user": address.lower(),
        "sizeThreshold": "0.1",
        "limit": limit,
        "sortBy": "CURRENT",
        "sortDirection": "DESC",
    })
    return api_get(f"{DATA_API}/positions?{params}&closed=true") or []


# ============================================================
# PARSEO
# ============================================================

def parse_city(title):
    match = re.search(r"temperature in (.+?) (?:be |between |\d)", title, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_condition(title):
    t = title.lower()
    if "or higher" in t or "or above" in t:
        return "at_or_above"
    elif "or below" in t:
        return "at_or_below"
    elif "between" in t:
        return "range"
    else:
        return "exact"


def parse_date(title):
    """Extrae fecha del título del mercado."""
    match = re.search(
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)"
        r"\s+\d+)",
        title, re.IGNORECASE
    )
    if not match:
        return None
    months = {
        "january":"01","february":"02","march":"03","april":"04",
        "may":"05","june":"06","july":"07","august":"08",
        "september":"09","october":"10","november":"11","december":"12"
    }
    parts = match.group(1).strip().split()
    if len(parts) != 2 or parts[0].lower() not in months:
        return None
    return f"2026-{months[parts[0].lower()]}-{parts[1].zfill(2)}"


def parse_temp(title):
    """Extrae temperatura y unidad."""
    match = re.search(r"(\d+)°([CF])", title)
    if match:
        return int(match.group(1)), match.group(2).upper()
    return None, None


def is_temperature_market(title):
    """Detecta si una posición es de un mercado de temperatura."""
    return bool(re.search(r"temperature", title, re.IGNORECASE))


# ============================================================
# DB
# ============================================================

def load_db():
    if not os.path.exists(DB_FILE):
        return {"traders": {}, "meta": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def get_trackable_traders(db):
    """
    Devuelve los traders que vale la pena analizar en profundidad.
    Excluye los marcados como 'reference' (ColdMath, Trader2) —
    los analizamos pero no generamos señales de ellos.
    """
    result = {}
    for name, info in db.get("traders", {}).items():
        addr = info.get("address", "")
        if not addr:
            continue
        result[name] = {
            "address": addr,
            "strategy": info.get("strategy", "unknown"),
            "is_reference": "reference" in info.get("tags", []),
        }
    return result


# ============================================================
# ANÁLISIS POR TRADER
# ============================================================

def analyze_trader(name, address, is_reference=False):
    """
    Analiza un trader. Devuelve dict con estadísticas + posiciones
    de temperatura en nuestro rango de precio (las señales).
    """
    positions = get_positions(address)
    closed = get_closed_positions(address, limit=100)

    # Win rate
    wins = sum(1 for p in closed if float(p.get("cashPnl", 0)) > 0)
    losses = sum(1 for p in closed if float(p.get("cashPnl", 0)) < 0)
    total_pnl = sum(float(p.get("cashPnl", 0)) for p in closed)
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0

    # Posiciones de temperatura activas
    temp_positions = [
        p for p in positions
        if is_temperature_market(p.get("title", ""))
    ]

    # Posiciones en nuestro rango de precio → señales potenciales
    signals = []
    for p in temp_positions:
        avg_price = float(p.get("avgPrice", 0))
        cur_price = float(p.get("curPrice", 0))

        if not (MIN_PRICE <= avg_price <= MAX_PRICE):
            continue

        title = p.get("title", "")
        city = parse_city(title)
        condition = parse_condition(title)
        market_date = parse_date(title)
        temp, unit = parse_temp(title)
        outcome = p.get("outcome", "")
        cash_pnl = float(p.get("cashPnl", 0))
        pct_pnl = float(p.get("percentPnl", 0))

        signals.append({
            "trader": name,
            "is_reference": is_reference,
            "title": title[:80],
            "city": city,
            "condition": condition,
            "date": market_date,
            "temp": temp,
            "unit": unit,
            "outcome": outcome,
            "avg_price": round(avg_price, 4),
            "cur_price": round(cur_price, 4),
            "cash_pnl": round(cash_pnl, 2),
            "pct_pnl": round(pct_pnl, 1),
            # Para que bot.py pueda matchear
            "match_key": f"{city}|{market_date}|{condition}|{temp}|{unit}",
        })

    # Distribución de precios (todas las posiciones activas)
    price_dist = {"low": 0, "mid": 0, "high": 0}
    for p in positions:
        pr = float(p.get("avgPrice", 0))
        if pr < 0.06:
            price_dist["low"] += 1
        elif pr <= 0.90:
            price_dist["mid"] += 1
        else:
            price_dist["high"] += 1

    # Ciudades
    cities = {}
    for p in temp_positions:
        city = parse_city(p.get("title", ""))
        if city:
            cities[city] = cities.get(city, 0) + 1

    return {
        "name": name,
        "address": address,
        "is_reference": is_reference,
        "n_positions": len(positions),
        "n_temp": len(temp_positions),
        "n_signals": len(signals),
        "win_rate": round(win_rate, 1),
        "wins": wins,
        "losses": losses,
        "pnl_closed": round(total_pnl, 2),
        "price_dist": price_dist,
        "cities": cities,
        "signals": signals,
    }


# ============================================================
# CONSENSO
# ============================================================

def find_consensus(all_results):
    """
    Detecta mercados donde 2+ traders coinciden.
    Usa match_key para identificar el mismo mercado.
    """
    market_to_signals = {}  # match_key → lista de señales

    for result in all_results:
        for signal in result["signals"]:
            key = signal["match_key"]
            if key not in market_to_signals:
                market_to_signals[key] = []
            # No duplicar el mismo trader
            if not any(s["trader"] == signal["trader"] for s in market_to_signals[key]):
                market_to_signals[key].append(signal)

    # Solo mercados con 2+ traders
    consensus = {
        k: v for k, v in market_to_signals.items()
        if len(v) >= 2
    }
    return consensus


# ============================================================
# SEÑALES PARA BOT.PY
# ============================================================

def generate_signals_file(all_results, consensus):
    """
    Genera signals.json que bot.py lee en cada ciclo.
    Estructura simple: lista de señales con toda la info necesaria
    para que bot.py pueda cruzar con sus propios candidatos.
    """
    # Todas las señales de traders no-reference
    actionable = []
    for result in all_results:
        if result["is_reference"]:
            continue
        for signal in result["signals"]:
            # Marcar si hay consenso
            signal["has_consensus"] = signal["match_key"] in consensus
            if signal["has_consensus"]:
                others = [
                    s["trader"] for s in consensus[signal["match_key"]]
                    if s["trader"] != signal["trader"]
                ]
                signal["consensus_with"] = others
            else:
                signal["consensus_with"] = []
            actionable.append(signal)

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "n_traders_analyzed": len(all_results),
        "n_actionable_signals": len(actionable),
        "n_consensus_markets": len(consensus),
        "signals": actionable,
    }

    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output


def get_trader_signals():
    """
    Función pública para bot.py.
    Lee signals.json y devuelve las señales.
    Si el archivo tiene más de 12 horas, devuelve vacío (stale).
    """
    if not os.path.exists(SIGNALS_FILE):
        return []

    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check freshness
        generated = datetime.fromisoformat(data["generated"])
        age_hours = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
        if age_hours > 12:
            return []

        return data.get("signals", [])
    except Exception:
        return []


# ============================================================
# GUARDAR HISTÓRICO
# ============================================================

def save_history(all_results, consensus):
    """Añade entrada al histórico acumulativo."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "traders": [
            {
                "name": r["name"],
                "n_positions": r["n_positions"],
                "n_temp": r["n_temp"],
                "n_signals": r["n_signals"],
                "win_rate": r["win_rate"],
                "pnl_closed": r["pnl_closed"],
                "price_dist": r["price_dist"],
                "top_cities": dict(sorted(r["cities"].items(), key=lambda x: -x[1])[:5]),
            }
            for r in all_results
        ],
        "n_consensus": len(consensus),
    }

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(entry)

    # Mantener solo últimas 50 entradas (evitar que crezca infinito)
    if len(history) > 50:
        history = history[-50:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ============================================================
# PRINTS
# ============================================================

def print_summary(all_results, consensus, signals_output):
    """Resumen legible para consola."""
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN DE ANÁLISIS")
    print(f"{'='*60}")

    for r in all_results:
        ref = " (REF)" if r["is_reference"] else ""
        print(f"\n  {r['name']}{ref} — {r['address'][:14]}...")
        print(f"    Posiciones: {r['n_positions']} total, {r['n_temp']} temp, "
              f"{r['n_signals']} en nuestro rango")
        print(f"    Win rate: {r['win_rate']:.1f}% ({r['wins']}W/{r['losses']}L) | "
              f"PnL: ${r['pnl_closed']:+.2f}")
        print(f"    Precios: low={r['price_dist']['low']} mid={r['price_dist']['mid']} "
              f"high={r['price_dist']['high']}")
        if r["cities"]:
            top_3 = sorted(r["cities"].items(), key=lambda x: -x[1])[:3]
            print(f"    Ciudades: {', '.join(f'{c}({n})' for c,n in top_3)}")

    # Señales accionables
    actionable = [s for s in signals_output.get("signals", []) if not s.get("is_reference")]
    if actionable:
        print(f"\n{'='*60}")
        print(f"🎯 SEÑALES ACCIONABLES ({len(actionable)})")
        print(f"{'='*60}")
        for s in actionable[:10]:
            consensus_mark = " 🤝" if s["has_consensus"] else ""
            print(f"\n  {s['trader']}: {s['outcome']} @ ${s['avg_price']:.3f} "
                  f"→ ${s['cur_price']:.3f}{consensus_mark}")
            print(f"    {s['city']} | {s['condition']} | {s['date']} | {s['temp']}°{s['unit']}")
            if s["consensus_with"]:
                print(f"    Consenso con: {', '.join(s['consensus_with'])}")
    else:
        print(f"\n  Sin señales accionables en este momento.")

    # Consenso
    if consensus:
        print(f"\n{'='*60}")
        print(f"🤝 MERCADOS CON CONSENSO ({len(consensus)})")
        print(f"{'='*60}")
        for key, sigs in consensus.items():
            traders = [s["trader"] for s in sigs]
            city = sigs[0].get("city", "?")
            date = sigs[0].get("date", "?")
            print(f"  {' + '.join(traders)}: {city} {date}")


# ============================================================
# FUNCIÓN PARA BOT.PY — Resumen Telegram
# ============================================================

def get_telegram_summary():
    """
    Genera un resumen corto para el comando /traders de Telegram.
    """
    if not os.path.exists(SIGNALS_FILE):
        return "📊 Sin datos de traders.\nEjecuta trader_analyzer.py primero."

    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return "❌ Error leyendo signals.json"

    generated = data.get("generated", "?")[:16]
    n_signals = data.get("n_actionable_signals", 0)
    n_consensus = data.get("n_consensus_markets", 0)

    text = f"📊 <b>Traders Intel</b>\n"
    text += f"Última actualización: {generated} UTC\n\n"

    if n_signals == 0:
        text += "Sin señales accionables ahora.\n"
    else:
        text += f"Señales: {n_signals} | Consenso: {n_consensus}\n\n"

        # Mostrar hasta 5 señales
        for s in data.get("signals", [])[:5]:
            if s.get("is_reference"):
                continue
            icon = "🤝" if s.get("has_consensus") else "📍"
            text += (f"{icon} {s['trader']}: {s['outcome']} {s['city']} "
                     f"{s['date']} ${s['avg_price']:.2f}\n")

    return text


# ============================================================
# MAIN
# ============================================================

def main(signals_only=False):
    print("=" * 60)
    print("📊 TRADER ANALYZER v2")
    print("=" * 60)

    db = load_db()
    traders = get_trackable_traders(db)

    if not traders:
        print("❌ No hay traders en traders_db.json")
        print("   Ejecuta find_traders.py primero.")
        return

    print(f"\nAnalizando {len(traders)} traders...")

    all_results = []
    for name, info in traders.items():
        print(f"\n  → {name}...")
        result = analyze_trader(name, info["address"], info["is_reference"])
        all_results.append(result)

        # Actualizar DB con stats frescas
        if name in db["traders"]:
            db["traders"][name].update({
                "last_analyzed": datetime.now(timezone.utc).isoformat(),
                "last_win_rate": result["win_rate"],
                "last_n_positions": result["n_positions"],
                "last_n_signals": result["n_signals"],
                "last_pnl_closed": result["pnl_closed"],
            })

        time.sleep(0.5)  # rate limit entre traders

    save_db(db)

    # Consenso
    consensus = find_consensus(all_results)

    # Generar signals.json
    signals_output = generate_signals_file(all_results, consensus)
    print(f"\n💾 {SIGNALS_FILE}: {signals_output['n_actionable_signals']} señales")

    if not signals_only:
        # Prints detallados
        print_summary(all_results, consensus, signals_output)

        # Histórico
        save_history(all_results, consensus)
        print(f"\n💾 Histórico actualizado en {HISTORY_FILE}")

    print(f"\n✅ Análisis completado.")
    print(f"   Bot.py puede leer señales con: from trader_analyzer import get_trader_signals")

    return signals_output


if __name__ == "__main__":
    signals_only = "--signals" in sys.argv
    main(signals_only=signals_only)
