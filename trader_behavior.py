"""
trader_behavior.py — Investigación: ¿cómo operan los traders exitosos?
======================================================================

Objetivo: entender si los traders que ganan dinero en Polymarket weather:
  1. Compran y esperan resolución (como nosotros)
  2. Venden antes de resolución (take-profit / stop-loss activos)
  3. Reciclan capital (abren y cierran muchas posiciones)

Método:
  - Analizar posiciones cerradas (win rate, PnL, patrón de cierre)
  - Buscar trades SELL en mercados donde el trader operó
  - Reconstruir timeline de cada posición

Uso:
    python trader_behavior.py
"""

import urllib.request
import urllib.parse
import json
import re
import time
from datetime import datetime, timezone

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

# Los 4 traders más rentables de nuestro tracking
TRADERS_TO_INVESTIGATE = {
    "Entire-Hood": {
        "address": "0xb40e89677d59665d5188541ad860450a6e2a7cc9",
        "wr": 84, "pnl": 4153,
    },
    "Thrifty-Original": {
        "address": "0xc34f6b088bb9172625ee1ea2ee8da9ac4f037d2e",
        "wr": 75, "pnl": 48,
    },
    "Small-Retirement": {
        "address": "0x1361f345f4bf87d1a39b46577e8e448abab9f12b",
        "wr": 59, "pnl": 395,
    },
    "ColdMath": {
        "address": "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11",
        "wr": 79, "pnl": 629, "note": "Ballena referencia",
    },
}


def api_get(url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-behavior/1.0")
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception as e:
            if attempt == retries - 1:
                print(f"    ⚠ API error: {e}")
                return None
            time.sleep(delay)
    return None


def is_temp_market(title):
    return bool(re.search(r"temperature", title, re.IGNORECASE))


# =================================================================
# PARTE 1: Análisis de posiciones (abiertas + cerradas)
# =================================================================

def get_all_positions(address, limit=100):
    """Obtiene TODAS las posiciones (abiertas + cerradas)."""
    # Posiciones activas
    params = urllib.parse.urlencode({
        "user": address.lower(),
        "sizeThreshold": "0",
        "limit": str(limit),
        "sortBy": "CURRENT",
        "sortDirection": "DESC",
    })
    active = api_get(f"{DATA_API}/positions?{params}") or []

    # Posiciones cerradas
    closed = api_get(f"{DATA_API}/positions?{params}&closed=true") or []

    return active, closed


def analyze_position_patterns(active, closed):
    """
    Clasifica posiciones por cómo terminaron.

    Clave: Si curPrice es 0.00 o 1.00, el mercado se resolvió.
    Si curPrice está entre 0.01 y 0.99, el trader vendió antes
    (o el mercado sigue abierto).
    """
    temp_active = [p for p in active if is_temp_market(p.get("title", ""))]
    temp_closed = [p for p in closed if is_temp_market(p.get("title", ""))]

    patterns = {
        "active_count": len(temp_active),
        "closed_count": len(temp_closed),
        "resolved_win": [],      # curPrice=1 (o 0 para NO) → ganó por resolución
        "resolved_loss": [],     # curPrice=0 (o 1 para NO) → perdió por resolución
        "sold_profit": [],       # curPrice intermedio, PnL > 0 → vendió con ganancia
        "sold_loss": [],         # curPrice intermedio, PnL < 0 → cortó pérdida
        "total_pnl": 0.0,
    }

    for p in temp_closed:
        cur_price = float(p.get("curPrice", 0))
        avg_price = float(p.get("avgPrice", 0))
        cash_pnl = float(p.get("cashPnl", 0))
        pct_pnl = float(p.get("percentPnl", 0))
        size = float(p.get("size", 0))
        initial = float(p.get("initialValue", 0))
        title = p.get("title", "")[:60]
        outcome = p.get("outcome", "?")

        patterns["total_pnl"] += cash_pnl

        entry = {
            "title": title,
            "outcome": outcome,
            "avg_price": avg_price,
            "cur_price": cur_price,
            "cash_pnl": cash_pnl,
            "pct_pnl": pct_pnl,
            "size": size,
            "initial": initial,
        }

        # Clasificar cómo terminó la posición
        # Resuelto = precio final en 0 o 1 (con margen de 0.02)
        if cur_price <= 0.02 or cur_price >= 0.98:
            if cash_pnl > 0:
                patterns["resolved_win"].append(entry)
            else:
                patterns["resolved_loss"].append(entry)
        else:
            # Precio intermedio = vendió antes de resolución
            if cash_pnl > 0:
                patterns["sold_profit"].append(entry)
            else:
                patterns["sold_loss"].append(entry)

    return patterns


# =================================================================
# PARTE 2: Buscar SELL trades en mercados específicos
# =================================================================

def find_sells_for_trader(address, condition_ids, max_markets=10):
    """
    Busca trades SELL de un trader específico en los mercados dados.
    Si encontramos SELLs, el trader gestiona activamente.
    """
    sells_found = []

    for i, cid in enumerate(condition_ids[:max_markets]):
        params = urllib.parse.urlencode({
            "market": cid,
            "limit": 500,
        })
        data = api_get(f"{DATA_API}/trades?{params}")
        if not data:
            continue

        for trade in data:
            trader_addr = trade.get("proxyWallet", "").lower()
            if trader_addr != address.lower():
                continue

            side = trade.get("side", "").upper()
            price = float(trade.get("price", 0))
            size = float(trade.get("size", 0))
            timestamp = trade.get("timestamp", "")

            sells_found.append({
                "side": side,
                "price": price,
                "size": size,
                "timestamp": timestamp,
                "market": cid[:16] + "...",
            })

        time.sleep(0.3)  # rate limit

    return sells_found


# =================================================================
# PARTE 3: Explorar endpoints de actividad del trader
# =================================================================

def explore_activity_endpoint(address):
    """
    Intenta diferentes endpoints para obtener historial de actividad.
    Los resultados nos dicen qué datos hay disponibles.
    """
    endpoints_to_try = [
        f"{DATA_API}/activity?user={address.lower()}&limit=20",
        f"{DATA_API}/activity?user={address.lower()}&limit=20&type=TRADE",
        f"{DATA_API}/trades?maker={address.lower()}&limit=20",
        f"{DATA_API}/trades?taker={address.lower()}&limit=20",
        f"{DATA_API}/trades?user={address.lower()}&limit=20",
    ]

    results = {}
    for url in endpoints_to_try:
        # Extraer el nombre del endpoint para el reporte
        endpoint_name = url.replace(DATA_API, "").split("?")[0] + "?" + url.split("?")[1].split("&")[0]
        data = api_get(url, retries=1, delay=1)
        if data is not None:
            if isinstance(data, list):
                results[endpoint_name] = {
                    "status": "OK",
                    "count": len(data),
                    "sample_keys": list(data[0].keys()) if data else [],
                    "sample": data[0] if data else None,
                }
            elif isinstance(data, dict):
                results[endpoint_name] = {
                    "status": "OK",
                    "keys": list(data.keys())[:10],
                    "sample": {k: str(v)[:100] for k, v in list(data.items())[:3]} if data else None,
                }
            else:
                results[endpoint_name] = {"status": "OK", "type": str(type(data))}
        else:
            results[endpoint_name] = {"status": "FAILED"}
        time.sleep(0.3)

    return results


# =================================================================
# EJECUCIÓN PRINCIPAL
# =================================================================

def main():
    print("=" * 65)
    print("🔬 INVESTIGACIÓN: Comportamiento de traders exitosos")
    print("=" * 65)

    # ---- Primero: explorar qué endpoints tenemos ----
    print("\n📡 Explorando endpoints de actividad...")
    test_addr = list(TRADERS_TO_INVESTIGATE.values())[0]["address"]
    endpoints = explore_activity_endpoint(test_addr)
    print(f"\n  Endpoints probados:")
    for name, result in endpoints.items():
        status = result["status"]
        if status == "OK":
            count = result.get("count", "?")
            keys = result.get("sample_keys", result.get("keys", []))
            print(f"  ✅ {name} → {count} resultados")
            print(f"      Campos: {', '.join(keys[:8])}")
        else:
            print(f"  ❌ {name} → No disponible")

    # ---- Analizar cada trader ----
    all_reports = []

    for name, info in TRADERS_TO_INVESTIGATE.items():
        addr = info["address"]
        print(f"\n{'='*65}")
        print(f"👤 {name} (WR={info['wr']}%, PnL=${info['pnl']:+})")
        note = info.get("note", "")
        if note:
            print(f"   {note}")
        print(f"{'='*65}")

        # Obtener posiciones
        print(f"\n  📊 Obteniendo posiciones...")
        active, closed = get_all_positions(addr)
        print(f"    Activas: {len(active)} | Cerradas: {len(closed)}")

        # Analizar patrones
        patterns = analyze_position_patterns(active, closed)

        n_rw = len(patterns["resolved_win"])
        n_rl = len(patterns["resolved_loss"])
        n_sp = len(patterns["sold_profit"])
        n_sl = len(patterns["sold_loss"])
        n_total = n_rw + n_rl + n_sp + n_sl

        print(f"\n  📈 POSICIONES DE TEMPERATURA CERRADAS: {n_total}")
        print(f"    ✅ Ganadas por resolución:    {n_rw}")
        print(f"    ❌ Perdidas por resolución:   {n_rl}")
        print(f"    💰 Vendidas con ganancia:     {n_sp}")
        print(f"    🔻 Vendidas con pérdida:      {n_sl}")

        # Tasa de gestión activa
        actively_managed = n_sp + n_sl
        held_to_resolution = n_rw + n_rl
        if n_total > 0:
            active_pct = actively_managed / n_total * 100
            hold_pct = held_to_resolution / n_total * 100
            print(f"\n  🎯 ESTRATEGIA:")
            print(f"    Gestión activa (venta antes de resolución): {actively_managed}/{n_total} ({active_pct:.0f}%)")
            print(f"    Hold-to-resolution:                         {held_to_resolution}/{n_total} ({hold_pct:.0f}%)")

        # Detalle de ventas con ganancia
        if n_sp > 0:
            avg_profit_pct = sum(p["pct_pnl"] for p in patterns["sold_profit"]) / n_sp
            min_profit = min(p["pct_pnl"] for p in patterns["sold_profit"])
            max_profit = max(p["pct_pnl"] for p in patterns["sold_profit"])
            print(f"\n  💰 Take-profit (vendidas con ganancia):")
            print(f"    PnL promedio: {avg_profit_pct:+.1f}%")
            print(f"    Rango: {min_profit:+.1f}% a {max_profit:+.1f}%")
            for p in sorted(patterns["sold_profit"], key=lambda x: -x["pct_pnl"])[:5]:
                print(f"      {p['outcome']:3s} ${p['avg_price']:.2f}→${p['cur_price']:.2f} "
                      f"PnL={p['pct_pnl']:+.1f}% (${p['cash_pnl']:+.2f}) | {p['title']}")

        # Detalle de ventas con pérdida (stop-loss)
        if n_sl > 0:
            avg_loss_pct = sum(p["pct_pnl"] for p in patterns["sold_loss"]) / n_sl
            min_loss = min(p["pct_pnl"] for p in patterns["sold_loss"])
            max_loss = max(p["pct_pnl"] for p in patterns["sold_loss"])
            print(f"\n  🔻 Stop-loss (vendidas con pérdida):")
            print(f"    PnL promedio: {avg_loss_pct:+.1f}%")
            print(f"    Rango: {min_loss:+.1f}% a {max_loss:+.1f}%")
            for p in sorted(patterns["sold_loss"], key=lambda x: x["pct_pnl"])[:5]:
                print(f"      {p['outcome']:3s} ${p['avg_price']:.2f}→${p['cur_price']:.2f} "
                      f"PnL={p['pct_pnl']:+.1f}% (${p['cash_pnl']:+.2f}) | {p['title']}")

        # Detalle de pérdidas por resolución (para comparar con nuestras)
        if n_rl > 0:
            avg_res_loss = sum(p["pct_pnl"] for p in patterns["resolved_loss"]) / n_rl
            total_res_loss = sum(p["cash_pnl"] for p in patterns["resolved_loss"])
            print(f"\n  ❌ Pérdidas por resolución (hold-to-end):")
            print(f"    PnL promedio: {avg_res_loss:+.1f}% | Total: ${total_res_loss:+.2f}")
            for p in sorted(patterns["resolved_loss"], key=lambda x: x["cash_pnl"])[:3]:
                print(f"      {p['outcome']:3s} ${p['avg_price']:.2f}→${p['cur_price']:.2f} "
                      f"PnL={p['pct_pnl']:+.1f}% (${p['cash_pnl']:+.2f}) | {p['title']}")

        # Posiciones activas
        temp_active = [p for p in active if is_temp_market(p.get("title", ""))]
        if temp_active:
            print(f"\n  📍 Posiciones activas ahora: {len(temp_active)}")
            # Buscar las que están en ganancia vs pérdida
            in_profit = sum(1 for p in temp_active if float(p.get("cashPnl", 0)) > 0)
            in_loss = sum(1 for p in temp_active if float(p.get("cashPnl", 0)) < 0)
            total_active_inv = sum(float(p.get("initialValue", 0)) for p in temp_active)
            print(f"    En ganancia: {in_profit} | En pérdida: {in_loss}")
            print(f"    Capital activo en temp: ${total_active_inv:.2f}")

        # Buscar SELL trades en mercados activos (muestreo)
        # Usar conditionIds de posiciones activas
        active_cids = []
        for p in temp_active[:5]:
            cid = p.get("conditionId", "")
            if cid:
                active_cids.append(cid)

        if active_cids:
            print(f"\n  🔍 Buscando trades BUY/SELL en {len(active_cids)} mercados activos...")
            all_trades = find_sells_for_trader(addr, active_cids, max_markets=5)

            buys = [t for t in all_trades if t["side"] == "BUY"]
            sells = [t for t in all_trades if t["side"] == "SELL"]

            print(f"    BUYs encontrados:  {len(buys)}")
            print(f"    SELLs encontrados: {len(sells)}")

            if sells:
                print(f"\n    📋 Detalle de SELLs:")
                for s in sells[:10]:
                    ts = s['timestamp']
                    ts_str = str(ts)[:16] if isinstance(ts, str) else datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if isinstance(ts, (int, float)) and ts > 0 else "?"
                    print(f"      SELL ${s['price']:.3f} × {s['size']:.1f} shares "
                          f"| {ts_str}")

        report = {
            "name": name,
            "wr": info["wr"],
            "pnl": info["pnl"],
            "temp_closed": n_total,
            "resolved_win": n_rw,
            "resolved_loss": n_rl,
            "sold_profit": n_sp,
            "sold_loss": n_sl,
            "active_mgmt_pct": active_pct if n_total > 0 else 0,
        }
        all_reports.append(report)

        time.sleep(1)  # rate limit entre traders

    # ---- Resumen comparativo ----
    print(f"\n\n{'='*65}")
    print(f"📊 RESUMEN COMPARATIVO")
    print(f"{'='*65}")
    print(f"\n{'Trader':<20} {'WR':>4} {'PnL':>8} {'Cerradas':>8} {'Res.Win':>8} "
          f"{'Res.Loss':>8} {'Vendió+':>8} {'Vendió-':>8} {'% Activo':>9}")
    print(f"{'-'*20} {'-'*4} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*9}")

    for r in all_reports:
        print(f"{r['name']:<20} {r['wr']:>3}% ${r['pnl']:>+6} {r['temp_closed']:>8} "
              f"{r['resolved_win']:>8} {r['resolved_loss']:>8} "
              f"{r['sold_profit']:>8} {r['sold_loss']:>8} "
              f"{r['active_mgmt_pct']:>8.0f}%")

    print(f"\n{'='*65}")
    print(f"🤖 NUESTRO BOT: 0% gestión activa (todo hold-to-resolution)")
    print(f"   Resultado: -$7.02 en 10 posiciones")
    print(f"{'='*65}")

    print(f"\n✅ Investigación completada.")
    print(f"   Siguiente paso: usar estos datos para decidir si implementar")
    print(f"   stop-loss, take-profit, o ambos en bot.py v11.")


if __name__ == "__main__":
    main()
