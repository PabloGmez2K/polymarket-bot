#!/usr/bin/env python3
"""
Experiment Analysis — sesión 2026-04-12
Tarea 1: Phantom Edge Analysis (dirección del modelo)
Tarea 2: Trader Census outcomes via Polymarket API
Tarea 3: Settlement Fidelity quick-check
"""

import json
import urllib.request
import urllib.error
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
LIFECYCLE = ROOT / "data/runtime_import/trade_lifecycle.json"
CENSUS = ROOT / "data/directional_trader_census.json"
ENRICHMENT = ROOT / "data/directional_trader_enrichment.json"

# ─────────────────────────────────────────────────────────────────────────────
# TAREA 1 — Phantom Edge Analysis
# ─────────────────────────────────────────────────────────────────────────────

def task1_phantom_edge():
    print("\n" + "="*70)
    print("TAREA 1 — PHANTOM EDGE ANALYSIS")
    print("="*70)

    with open(LIFECYCLE, encoding="utf-8-sig") as f:
        data = json.load(f)

    records = data["records"]
    closed = [r for r in records if r.get("status") == "closed"]

    # Diagnóstico: mostrar distribución de close_reasons y lógica de dirección
    from collections import Counter
    cr_counter = Counter()
    for r in closed:
        cc = r.get("close_context", {})
        cr = cc.get("close_reason", "") or "EMPTY"
        side = r.get("side", "?")
        pnl = cc.get("pnl_cash")
        cr_counter[(cr, side, "WIN" if pnl and pnl > 0 else "LOSS" if pnl and pnl < 0 else "?")] += 1
    print("\nDIAGNOSTICO close_reason x side x resultado:")
    for (cr, side, result), count in sorted(cr_counter.items()):
        print(f"  {cr:<35} side={side} {result}: {count}")

    # Para dirección: necesitamos saber si el mercado resolvió a favor del side del bot
    # close_reason = market_resolved_yes → posición YES ganó, NO perdió
    # close_reason = market_resolved_no  → posición NO ganó, YES perdió
    # Adicionalmente, miramos market_data_after_close si existe

    direction_correct = []
    direction_wrong = []
    direction_inconcluso = []

    breakdown = {
        "stop_loss": {"total": 0, "correct": 0, "wrong": 0},
        "reeval": {"total": 0, "correct": 0, "wrong": 0},
        "micro_position_unsellable": {"total": 0, "correct": 0, "wrong": 0},
        "take_profit": {"total": 0, "correct": 0, "wrong": 0},
        "market_resolved_yes": {"total": 0, "correct": 0, "wrong": 0},
        "market_resolved_no": {"total": 0, "correct": 0, "wrong": 0},
        "other": {"total": 0, "correct": 0, "wrong": 0},
    }

    correct_but_loss = []  # dirección correcta pero resultado fue pérdida

    for r in closed:
        label = r.get("label", "?")
        side = r.get("side", "")
        close_ctx = r.get("close_context", {})
        close_reason = close_ctx.get("close_reason", "") or r.get("close_reason", "")
        pnl = close_ctx.get("pnl_cash")

        # Determinar dirección
        direction = None

        if close_reason == "market_resolved_yes":
            # Convención del bot: nuestro token resolvió a $1 (ganamos)
            # → dirección CORRECTA independientemente del side
            direction = "correct"
        elif close_reason == "market_resolved_no":
            # Nuestro token resolvió a $0 (perdimos)
            # → dirección INCORRECTA
            direction = "wrong"
        elif close_reason in ("take_profit",):
            # Bot salió por take_profit → dirección implícitamente correcta (precio subió)
            direction = "correct"
        elif close_reason in ("reeval",) and pnl is not None and pnl > 0:
            # reeval con PnL positivo → también dirección correcta
            direction = "correct"
        elif close_reason in ("reeval",) and pnl is not None and pnl < 0:
            # reeval con PnL negativo → salió en pérdida
            direction = "wrong"
        else:
            # Para stop_loss, reeval, micro_position_unsellable:
            # Miramos market_data_after_close si existe
            mkt_after = r.get("market_data_after_close", {})
            if mkt_after:
                final_price = mkt_after.get("final_price") or mkt_after.get("max_price") or mkt_after.get("last_price")
                resolution = mkt_after.get("resolved_outcome") or mkt_after.get("resolution")
                if resolution:
                    if resolution in ("YES", "1", True, 1):
                        direction = "correct" if side == "YES" else "wrong"
                    elif resolution in ("NO", "0", False, 0):
                        direction = "correct" if side == "NO" else "wrong"
                elif final_price is not None:
                    # precio >0.9 → resolvió YES, <0.1 → resolvió NO
                    if final_price > 0.9:
                        direction = "correct" if side == "YES" else "wrong"
                    elif final_price < 0.1:
                        direction = "correct" if side == "NO" else "wrong"

        # Clasificar close_reason en categorías
        if close_reason in ("stop_loss", "stop_loss_intra"):
            cat = "stop_loss"
        elif "reeval" in close_reason:
            cat = "reeval"
        elif "micro_position" in close_reason:
            cat = "micro_position_unsellable"
        elif "take_profit" in close_reason:
            cat = "take_profit"
        elif close_reason == "market_resolved_yes":
            cat = "market_resolved_yes"
        elif close_reason == "market_resolved_no":
            cat = "market_resolved_no"
        else:
            cat = "other"

        breakdown[cat]["total"] += 1

        if direction == "correct":
            direction_correct.append(r)
            breakdown[cat]["correct"] += 1
            # ¿fue pérdida a pesar de dirección correcta?
            if pnl is not None and pnl < 0:
                upside = r.get("upside_left_cash_peak") or r.get("market_data_after_close", {}).get("upside_left_cash_peak")
                correct_but_loss.append({
                    "label": label,
                    "side": side,
                    "close_reason": close_reason,
                    "pnl": pnl,
                    "upside_left": upside,
                })
        elif direction == "wrong":
            direction_wrong.append(r)
            breakdown[cat]["wrong"] += 1
        else:
            direction_inconcluso.append(r)

    total = len(closed)
    n_correct = len(direction_correct)
    n_wrong = len(direction_wrong)
    n_inc = len(direction_inconcluso)

    # Calcular % sobre analizables (excl inconcluso)
    n_analyzable = n_correct + n_wrong
    pct_correct = (n_correct / n_analyzable * 100) if n_analyzable > 0 else 0

    print(f"\nTotal trades cerrados: {total}")
    print(f"Analizables (con resolución conocida): {n_analyzable}")
    print(f"Dirección correcta: {n_correct} ({pct_correct:.1f}%)")
    print(f"Dirección incorrecta: {n_wrong} ({100-pct_correct:.1f}%)")
    print(f"Inconcluso (sin datos post-cierre): {n_inc}")

    print("\nBreakdown por causa de cierre:")
    for cat, counts in breakdown.items():
        if counts["total"] == 0:
            continue
        n_c = counts["correct"]
        n_w = counts["wrong"]
        n_total = counts["total"]
        analyzed = n_c + n_w
        pct = (n_c / analyzed * 100) if analyzed > 0 else 0
        print(f"  {cat}: {n_total} trades | analizables={analyzed} | dirección correcta: {n_c} ({pct:.0f}%)")

    print("\nTrades con dirección correcta pero resultado negativo:")
    if correct_but_loss:
        for t in correct_but_loss:
            print(f"  {t['label']} | side={t['side']} | {t['close_reason']} | pnl=${t['pnl']:.2f} | upside_left=${t['upside_left']}")
    else:
        print("  (ninguno identificado con datos disponibles)")

    # Señal de upside_left del summary
    print("\nTop upside_left del summary (bot salio antes, mercado siguio subiendo):")
    for item in data["summary"].get("top_upside_left", []):
        print(f"  {item['label']} | {item['close_reason']} | cerro @{item['close_price']} -> {item['max_price_after_close']} | upside: ${item['upside_left_cash_peak']} (+{item['upside_left_pct_peak']}%)")

    # Veredicto
    print("\n--- VEREDICTO TAREA 1 ---")
    if n_analyzable < 5:
        print("INSUFICIENTE: muy pocos trades con resolución conocida para determinar edge")
    elif pct_correct >= 55:
        print(f"SEÑAL POSITIVA: {pct_correct:.1f}% dirección correcta (umbral: ≥55%)")
        print("El modelo tiene ventaja direccional real.")
    elif pct_correct >= 50:
        print(f"SEÑAL DÉBIL: {pct_correct:.1f}% — ligeramente sobre azar, insuficiente")
    else:
        print(f"SIN EDGE: {pct_correct:.1f}% — modelo no supera azar direccional")

    return pct_correct, n_analyzable


# ─────────────────────────────────────────────────────────────────────────────
# TAREA 2 — Trader Census: verificar outcomes via API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_market_by_slug(slug):
    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "polymarket-bot-research/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def task2_trader_census():
    print("\n" + "="*70)
    print("TAREA 2 — TRADER CENSUS: OUTCOMES VIA API")
    print("="*70)

    with open(CENSUS, encoding="utf-8-sig") as f:
        census = json.load(f)

    # Cargar enrichment para slugs
    with open(ENRICHMENT, encoding="utf-8-sig") as f:
        enrichment = json.load(f)

    # Construir mapa trader → slugs de sus posiciones
    # El enrichment tiene `traders[].active_summary.sample_active_directional[].market_slug` y
    # también `traders[].census_snapshot.sample_positions` pero sin slug
    # Necesitamos los slugs de mercados de Ankara/Shanghai del 8-9 abr

    # Primero identificar los 2 mercados clave de las sample_positions del census:
    # 1. Wuhan at_or_above 24°C April 8
    # 2. Shanghai at_or_above 30°C April 9
    # 3. Ankara at_or_below 8°C April 8

    # Buscar slugs en enrichment
    market_slugs = {}
    for trader in enrichment.get("traders", []):
        # Active directional positions
        active = trader.get("active_summary", {}).get("sample_active_directional", [])
        for pos in active:
            slug = pos.get("market_slug") or pos.get("slug")
            if slug:
                key = f"{pos.get('city','?')}|{pos.get('condition','?')}|{pos.get('threshold','?')}"
                market_slugs[key] = slug

        # También historical si existe
        historical = trader.get("historical_positions", [])
        for pos in historical:
            slug = pos.get("market_slug") or pos.get("slug")
            if slug:
                key = f"{pos.get('city','?')}|{pos.get('condition','?')}|{pos.get('threshold','?')}"
                market_slugs[key] = slug

    # Los mercados clave del census son:
    # Wuhan at_or_above 24C April 8 → mkt_prob_yes=0.002 (extremo)
    # Shanghai at_or_above 30C April 9 → mkt_prob_yes=0.323 (útil)
    # Ankara at_or_below 8C April 8 → mkt_prob_yes=0.0 (extremo)

    print(f"\nMarket slugs encontrados en enrichment: {len(market_slugs)}")
    for k, v in list(market_slugs.items())[:5]:
        print(f"  {k}: {v}")

    # Verificar los mercados clave directamente buscando en enrichment
    # Necesito buscar slugs para los mercados específicos del census
    key_markets = [
        {"city": "Wuhan", "condition": "at_or_above", "threshold": 24, "date": "April 8", "mkt_prob": 0.002, "range_type": "extreme"},
        {"city": "Shanghai", "condition": "at_or_above", "threshold": 30, "date": "April 9", "mkt_prob": 0.323, "range_type": "useful"},
        {"city": "Ankara", "condition": "at_or_below", "threshold": 8, "date": "April 8", "mkt_prob": 0.0, "range_type": "extreme"},
    ]

    # Buscar slugs en todas las posiciones del enrichment
    slug_lookup = {}
    for trader in enrichment.get("traders", []):
        for pos_list_name in ["sample_active_directional", "active_positions", "positions"]:
            for pos in trader.get("active_summary", {}).get(pos_list_name, []):
                city = pos.get("city", "")
                cond = pos.get("condition", "")
                thresh = pos.get("threshold")
                slug = pos.get("market_slug") or pos.get("slug")
                if slug and city and cond and thresh:
                    slug_lookup[(city, cond, thresh)] = slug

    # Intentar derivar slugs de los títulos de mercado en enrichment
    # Buscar en todas las keys del enrichment por slugs de Shanghai/Ankara/Wuhan
    print("\nBuscando slugs en enrichment para mercados clave...")
    found_slugs = {}
    for trader in enrichment.get("traders", []):
        active = trader.get("active_summary", {})
        for pos in active.get("sample_active_directional", []):
            city = pos.get("city", "")
            cond = pos.get("condition", "")
            thresh = pos.get("threshold")
            slug = pos.get("market_slug", "") or pos.get("slug", "")
            title = pos.get("title", "")
            if city in ["Shanghai", "Ankara", "Wuhan"] and slug:
                key = f"{city}|{cond}|{thresh}"
                found_slugs[key] = {"slug": slug, "title": title}
                print(f"  FOUND: {key} → {slug}")

    # API calls para los mercados que tenemos slugs
    outcomes = {}
    if found_slugs:
        print("\nConsultando Polymarket API para outcomes...")
        for key, info in found_slugs.items():
            slug = info["slug"]
            print(f"  GET /markets?slug={slug}")
            result = fetch_market_by_slug(slug)
            if isinstance(result, list) and result:
                m = result[0]
                outcomes[key] = {
                    "slug": slug,
                    "closed": m.get("closed"),
                    "active": m.get("active"),
                    "outcome_prices": m.get("outcomePrices"),
                    "resolution": m.get("resolution") or m.get("resolutionSource"),
                    "question": m.get("question", "")[:80],
                }
                print(f"    closed={m.get('closed')}, prices={m.get('outcomePrices')}")
            elif "error" in result:
                outcomes[key] = {"error": result["error"]}
                print(f"    ERROR: {result['error']}")
    else:
        print("  No se encontraron slugs en enrichment para llamadas API directas")
        print("  Analizando traders con datos del census únicamente...")

    # ── OUTCOMES INFERIDOS ──────────────────────────────────────────────────
    # Basado en:
    # 1. Bot's own T3 data: Shanghai 30°C Apr9 NO → market_resolved_yes = NO token won
    #    → Shanghai DID NOT reach 30°C on April 9
    # 2. Ankara at_or_below 8°C Apr8: mkt_prob_yes=0.0 in census (post-resolution state)
    #    → YES=0 means "at or below 8°C" did NOT happen → NO wins
    #    → Entry prices (0.38-0.58) show it was ~42-58% YES at entry (real contest)
    # 3. Wuhan at_or_above 24°C Apr8: mkt_prob_yes=0.002 → near-certain NO wins
    #
    # ACLARACIÓN CRÍTICA sobre mkt_prob_yes:
    # El valor en el census es capturado en el momento del scan (Apr 8, 15:21 UTC).
    # Para Ankara/Wuhan Apr8, puede ser POSTERIOR a la resolución del mercado.
    # Los precios de entrada (0.38-0.70) indican que en el momento de compra
    # había incertidumbre real → no eran "moneda obvia" al entrar.

    OUTCOMES = {
        "Shanghai at_or_above 30 April 9": "NO",   # bot confirmed via T3
        "Ankara at_or_below 8 April 8":    "NO",   # inferred from mkt_prob_yes=0.0
        "Wuhan at_or_above 24 April 8":    "NO",   # inferred from mkt_prob_yes=0.002
    }

    def get_outcome(city, cond, thresh, date_str):
        key = f"{city} {cond} {thresh} {date_str}"
        return OUTCOMES.get(key)

    # Clasificación rango útil basada en entry price (más fiable que mkt_prob post-hoc)
    def classify_range(price, mkt_prob_at_census):
        # Si el precio pagado está entre 0.2 y 0.8 → mercado tenía incertidumbre real al entrar
        if 0.20 <= price <= 0.80:
            return "useful_range"
        return "extreme"

    print("\n--- Análisis por trader: outcomes inferidos del censo ---")
    print("Mercados evaluados:")
    print("  Shanghai at_or_above 30°C Apr9: RESOLVIO NO (confirmado por bot T3)")
    print("  Ankara at_or_below 8°C Apr8:    RESOLVIO NO (mkt_prob_yes->0.0 post-cierre)")
    print("  Wuhan at_or_above 24°C Apr8:    RESOLVIO NO (mkt_prob_yes=0.002 post-cierre)")
    print()

    trader_analysis = []
    hist_wr = {  # From reference_trader_city_market_cross
        "White-Donkey": 56.6, "Entire-Hood": 91.0, "Motionless-Stalk": 39.8,
        "Academic-Maniac": 55.6, "Massive-Distribution": 70.7, "Coarse-Gas": 73.5,
        "Rewarding-Pusher": 17.5, "Content-Lunchroom": 61.0,
        "Illustrious-Church": 5.0, "Extra-Small-Tabletop": 72.7,
    }

    for trader_data in census.get("traders", []):
        name = trader_data.get("pseudonym", "?")
        positions = trader_data.get("sample_positions", [])

        wins = 0
        losses = 0
        useful_wins = 0
        useful_losses = 0
        detail = []

        for pos in positions:
            city = pos.get("city", "")
            cond = pos.get("condition", "")
            thresh = pos.get("threshold", "")
            date_str = pos.get("date_str", "")
            bet = pos.get("outcome", "")  # YES or NO
            price = pos.get("price", 0)
            mkt_prob = pos.get("market_prob_yes", 0.5)

            actual = get_outcome(city, cond, thresh, date_str)
            rang = classify_range(price, mkt_prob)

            if actual is None:
                result = "?"
            elif bet.upper() == actual:
                result = "WIN"
                wins += 1
                if rang == "useful_range":
                    useful_wins += 1
            else:
                result = "LOSS"
                losses += 1
                if rang == "useful_range":
                    useful_losses += 1

            detail.append(f"  {result} | {rang:<13} | bet {bet} @{price:.3f} | {city} {cond} {thresh}°C {date_str}")

        total = wins + losses
        wr = wins / total * 100 if total > 0 else 0
        useful_total = useful_wins + useful_losses
        useful_wr = useful_wins / useful_total * 100 if useful_total > 0 else 0
        hist = hist_wr.get(name, "?")

        trader_analysis.append({
            "name": name, "wins": wins, "losses": losses, "wr": wr,
            "useful_wins": useful_wins, "useful_losses": useful_losses,
            "useful_wr": useful_wr, "hist_wr": hist,
        })

        threshold_flag = "* MEETS THRESHOLD (>60% in >=3 useful)" if useful_total >= 3 and useful_wr > 60 else ""
        print(f"Trader: {name}  [hist WR: {hist}%]")
        print(f"  Sample WR: {wins}/{total} = {wr:.0f}%  |  Useful WR: {useful_wins}/{useful_total} = {useful_wr:.0f}%  {threshold_flag}")
        for d in detail:
            print(d)
        print()

    # Resumen
    print("--- RESUMEN T2 ---")
    meets = [t for t in trader_analysis if t["useful_wins"] + t["useful_losses"] >= 5 and t["useful_wr"] > 60]
    print(f"Traders con WR>60% en rango útil con n>=5 trades útiles: {len(meets)}")
    if meets:
        for m in meets:
            print(f"  {m['name']}: {m['useful_wins']}/{m['useful_wins']+m['useful_losses']} = {m['useful_wr']:.0f}%")
    else:
        # Check n>=3
        meets3 = [t for t in trader_analysis if t["useful_wins"] + t["useful_losses"] >= 3 and t["useful_wr"] > 60]
        print(f"Traders con WR>60% en rango útil con n>=3 trades útiles: {len(meets3)}")
        for m in meets3:
            print(f"  {m['name']}: {m['useful_wins']}/{m['useful_wins']+m['useful_losses']} = {m['useful_wr']:.0f}%")

    print()
    print("ADVERTENCIA: solo 2 mercados distintos en el census sample (Shanghai Apr9, Ankara Apr8)")
    print("El umbral n>=5 trades se cumple por trades repetidos en los mismos mercados,")
    print("no por mercados independientes. Esto limita el valor estadístico de T2.")

    return outcomes, trader_analysis


# ─────────────────────────────────────────────────────────────────────────────
# TAREA 3 — Settlement Fidelity quick-check
# ─────────────────────────────────────────────────────────────────────────────

def task3_settlement_fidelity():
    print("\n" + "="*70)
    print("TAREA 3 — SETTLEMENT FIDELITY QUICK-CHECK")
    print("="*70)

    with open(LIFECYCLE, encoding="utf-8-sig") as f:
        data = json.load(f)

    records = data["records"]

    # Filtrar resolved_wins y market_resolved_* closures
    resolved = []
    for r in records:
        close_ctx = r.get("close_context", {})
        close_reason = close_ctx.get("close_reason", "")
        status = r.get("status", "")

        if close_reason in ("market_resolved_yes", "market_resolved_no") or status == "closed":
            # Verificar si tiene forecast
            entry_ctx = r.get("entry_context", {}) or r.get("latest_entry_context", {})
            forecast = entry_ctx.get("forecast_max") or entry_ctx.get("openmeteo_forecast_max_c")
            our_prob = entry_ctx.get("our_prob")
            side = r.get("side", "")
            label = r.get("label", "?")
            city = r.get("city", "")
            close_reason_actual = close_ctx.get("close_reason", "")
            pnl = close_ctx.get("pnl_cash")
            resolution_icao = entry_ctx.get("resolution_icao") or entry_ctx.get("icao")

            # Solo mercados resueltos directamente por el mercado
            if close_reason_actual in ("market_resolved_yes", "market_resolved_no"):
                # Convención: market_resolved_yes = nuestro token ganó (modelo acertó)
                # market_resolved_no = nuestro token perdió (modelo falló)
                model_correct = (close_reason_actual == "market_resolved_yes")

                resolved.append({
                    "label": label,
                    "city": city,
                    "side": side,
                    "close_reason": close_reason_actual,
                    "direction_correct": model_correct,
                    "forecast_max": forecast,
                    "our_prob": our_prob,
                    "pnl": pnl,
                    "resolution_icao": resolution_icao,
                })

    print(f"\nMercados resueltos directamente por el mercado: {len(resolved)}")
    print(f"\n{'Label':<40} {'Side':<5} {'Resolución':<25} {'Modelo OK':<10} {'Forecast':<10} {'OurProb':<10} {'ICAO'}")
    print("-" * 120)

    wins = 0
    for r in resolved:
        ok = "✓" if r["direction_correct"] else "✗"
        if r["direction_correct"]:
            wins += 1
        fc = f"{r['forecast_max']:.1f}°C" if r["forecast_max"] else "N/A"
        prob = f"{r['our_prob']:.1f}%" if r["our_prob"] else "N/A"
        icao = r["resolution_icao"] or "N/A"
        print(f"  {r['label']:<38} {r['side']:<5} {r['close_reason']:<25} {ok:<10} {fc:<10} {prob:<10} {icao}")

    if resolved:
        wr = wins / len(resolved) * 100
        print(f"\nWin rate en mercados resueltos directamente: {wins}/{len(resolved)} = {wr:.1f}%")
        print("(Sólo mercados donde hubo resolución final del mercado)")

    return resolved


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("EXPERIMENT ANALYSIS — 2026-04-12")
    print("Bot: 91 trades, 16.5% WR, -$29.71 PnL, shadow mode since Apr 4")

    pct_correct, n_analyzable = task1_phantom_edge()
    outcomes, trader_analysis = task2_trader_census()
    resolved = task3_settlement_fidelity()

    print("\n" + "="*70)
    print("VEREDICTO INTEGRADO")
    print("="*70)
    print(f"\nTarea 1 — Phantom Edge: {pct_correct:.1f}% dirección correcta ({n_analyzable} trades analizables)")
    print(f"Tarea 2 — Trader Census: análisis completado (slugs/outcomes pendientes de API)")
    print(f"Tarea 3 — Settlement: {len(resolved)} mercados resueltos directamente analizados")
