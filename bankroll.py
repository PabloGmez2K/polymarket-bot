import json
import math

# =============================================================
# bankroll.py — Gestión de Riesgo y Tamaño de Apuestas
# Sesión 2 del bot de Polymarket
# =============================================================
#
# Este módulo calcula CUÁNTO apostar en cada operación.
#
# Concepto clave: EL CRITERIO DE KELLY
#
# Imagina que tienes una moneda trucada que sale cara el 60%
# de las veces. ¿Cuánto deberías apostar en cada lanzamiento?
#
# - Si apuestas todo: una sola cruz y estás arruinado.
# - Si apuestas muy poco: tardas una eternidad en ganar.
# - El punto óptimo: apostar un % específico que maximiza
#   el crecimiento a largo plazo sin riesgo de ruina.
#
# La fórmula de Kelly:
#
#   f* = (p * b - q) / b
#
# Donde:
#   f* = fracción óptima de tu bankroll a apostar
#   p  = probabilidad de ganar (nuestra estimación)
#   q  = probabilidad de perder (1 - p)
#   b  = odds (cuánto ganas por cada $1 apostado)
#
# En Polymarket, si compras YES a $0.30 y ganas, recibes $1.00.
# Así que b = (1.00 - 0.30) / 0.30 = 2.33
# (Ganas $0.70 por cada $0.30 que arriesgas)
#
# MEDIO KELLY: En la práctica, los traders usan "medio Kelly"
# (la mitad de lo que dice la fórmula) porque:
# - Nuestras estimaciones de probabilidad no son perfectas
# - Es mejor ser conservador que agresivo
# - Medio Kelly da ~75% del retorno de Kelly completo
#   pero con mucho menos riesgo de pérdidas grandes
# =============================================================


def kelly_fraction(estimated_prob, market_price):
    """
    Calcula la fracción de Kelly para una apuesta.

    Parámetros:
        estimated_prob: nuestra estimación de probabilidad (0 a 1)
                       Ejemplo: 0.70 = creemos que hay 70% de chance
        market_price:   precio actual en Polymarket (0 a 1)
                       Ejemplo: 0.30 = comprar YES cuesta $0.30

    Retorna:
        Fracción del bankroll a apostar (0 a 1).
        0 = no apostar (no hay edge o edge negativo)

    Ejemplo:
        Si creemos que la probabilidad es 0.70 y el precio es 0.30:
        b = (1 - 0.30) / 0.30 = 2.33  (odds)
        f* = (0.70 * 2.33 - 0.30) / 2.33 = 0.57
        Medio Kelly = 0.57 / 2 = 0.285 (apostar 28.5% del bankroll)
    """
    if market_price <= 0 or market_price >= 1:
        return 0.0

    if estimated_prob <= 0 or estimated_prob >= 1:
        return 0.0

    # Calcular odds
    # b = cuánto ganas por cada $1 que arriesgas
    b = (1.0 - market_price) / market_price

    # Probabilidades
    p = estimated_prob  # Prob de ganar
    q = 1.0 - p         # Prob de perder

    # Fórmula de Kelly
    kelly = (p * b - q) / b

    # Si Kelly es negativo, no hay edge → no apostar
    if kelly <= 0:
        return 0.0

    # Medio Kelly (más conservador)
    half_kelly = kelly / 2.0

    # Límite máximo de seguridad: nunca más del 5% del bankroll
    # Esto es una capa extra de protección por si nuestro modelo
    # tiene un error grande en alguna estimación
    return min(half_kelly, 0.05)


def calculate_position(bankroll, estimated_prob, market_price, min_bet=0.50):
    """
    Calcula el tamaño concreto de la posición en dólares.

    Parámetros:
        bankroll:       tu capital total en USD
        estimated_prob: nuestra estimación de probabilidad (0 a 1)
        market_price:   precio en Polymarket (0 a 1)
        min_bet:        apuesta mínima en USD (Polymarket tiene mínimos)

    Retorna dict con:
        - fraction: % del bankroll
        - amount: cantidad en USD
        - shares: número de shares que compras
        - potential_profit: ganancia si aciertas
        - potential_loss: pérdida si fallas
        - expected_value: ganancia esperada (probabilística)
    """
    fraction = kelly_fraction(estimated_prob, market_price)

    if fraction <= 0:
        return {
            "fraction": 0,
            "amount": 0,
            "shares": 0,
            "potential_profit": 0,
            "potential_loss": 0,
            "expected_value": 0,
            "recommendation": "NO APOSTAR — sin edge",
        }

    # Cantidad a apostar
    amount = bankroll * fraction

    # Redondear a centavos
    amount = round(amount, 2)

    # Respetar mínimo
    if amount < min_bet:
        return {
            "fraction": fraction,
            "amount": 0,
            "shares": 0,
            "potential_profit": 0,
            "potential_loss": 0,
            "expected_value": 0,
            "recommendation": f"NO APOSTAR — tamaño ({amount:.2f}) menor que mínimo ({min_bet:.2f})",
        }

    # Número de shares (cada share cuesta market_price y paga $1 si ganas)
    shares = amount / market_price

    # Si ganas: recibes $1 por share, tu ganancia neta es shares * (1 - price)
    potential_profit = round(shares * (1.0 - market_price), 2)

    # Si pierdes: pierdes todo lo apostado
    potential_loss = round(amount, 2)

    # Valor esperado: (prob_ganar * ganancia) - (prob_perder * pérdida)
    ev = estimated_prob * potential_profit - (1 - estimated_prob) * potential_loss
    ev = round(ev, 2)

    return {
        "fraction": round(fraction * 100, 2),  # En porcentaje
        "amount": amount,
        "shares": round(shares, 2),
        "potential_profit": potential_profit,
        "potential_loss": potential_loss,
        "expected_value": ev,
        "recommendation": "APOSTAR",
    }


def simulate_bankroll_growth(bankroll, trades):
    """
    Simula cómo evolucionaría el bankroll con una serie de trades.

    'trades' es una lista de dicts con:
        - estimated_prob: nuestra probabilidad estimada
        - market_price: precio de compra
        - won: True/False (si ganamos)

    Devuelve la evolución del bankroll paso a paso.
    """
    history = [bankroll]
    current = bankroll

    for trade in trades:
        pos = calculate_position(
            current,
            trade["estimated_prob"],
            trade["market_price"],
        )

        if pos["amount"] == 0:
            history.append(current)
            continue

        if trade["won"]:
            current += pos["potential_profit"]
        else:
            current -= pos["potential_loss"]

        current = round(current, 2)
        history.append(current)

    return history


# =============================================================
# DEMO: Mostrar cómo funciona el sistema de bankroll
# =============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("  SISTEMA DE GESTIÓN DE RIESGO — Demo")
    print("=" * 60)
    print()

    # Configuración del usuario
    BANKROLL = 100.00  # Capital inicial en USD

    print(f"  Bankroll inicial: ${BANKROLL:.2f}")
    print()

    # ---- EJEMPLO 1: Edge grande ----
    print("  --- Ejemplo 1: Edge grande ---")
    print("  Nuestra estimación: 70% probabilidad de YES")
    print("  Precio Polymarket:  $0.30 (mercado cree 30%)")
    print()

    pos = calculate_position(BANKROLL, 0.70, 0.30)
    print(f"  Kelly dice: apostar {pos['fraction']}% del bankroll")
    print(f"  Cantidad:   ${pos['amount']:.2f}")
    print(f"  Shares:     {pos['shares']:.1f}")
    print(f"  Si ganas:   +${pos['potential_profit']:.2f}")
    print(f"  Si pierdes: -${pos['potential_loss']:.2f}")
    print(f"  Valor esperado: ${pos['expected_value']:.2f}")
    print()

    # ---- EJEMPLO 2: Edge pequeño ----
    print("  --- Ejemplo 2: Edge pequeño ---")
    print("  Nuestra estimación: 55% probabilidad de YES")
    print("  Precio Polymarket:  $0.45 (mercado cree 45%)")
    print()

    pos = calculate_position(BANKROLL, 0.55, 0.45)
    print(f"  Kelly dice: apostar {pos['fraction']}% del bankroll")
    print(f"  Cantidad:   ${pos['amount']:.2f}")
    print(f"  Shares:     {pos['shares']:.1f}")
    print(f"  Si ganas:   +${pos['potential_profit']:.2f}")
    print(f"  Si pierdes: -${pos['potential_loss']:.2f}")
    print(f"  Valor esperado: ${pos['expected_value']:.2f}")
    print()

    # ---- EJEMPLO 3: Sin edge (no apostar) ----
    print("  --- Ejemplo 3: Sin edge ---")
    print("  Nuestra estimación: 40% probabilidad de YES")
    print("  Precio Polymarket:  $0.50 (mercado cree 50%)")
    print()

    pos = calculate_position(BANKROLL, 0.40, 0.50)
    print(f"  {pos['recommendation']}")
    print()

    # ---- SIMULACIÓN: 20 trades con 65% de aciertos ----
    print("  " + "=" * 56)
    print("  SIMULACIÓN: 20 trades con edge moderado")
    print("  " + "=" * 56)
    print()

    import random
    random.seed(42)  # Semilla fija para reproducibilidad

    trades = []
    for i in range(20):
        # Simulamos edge moderado: estimamos 65%, compramos a $0.45
        est_prob = 0.65
        mkt_price = 0.45
        # 65% de los trades son ganadores (según nuestra estimación real)
        won = random.random() < est_prob
        trades.append({
            "estimated_prob": est_prob,
            "market_price": mkt_price,
            "won": won,
        })

    history = simulate_bankroll_growth(BANKROLL, trades)

    print(f"  Bankroll inicial:  ${history[0]:.2f}")
    print()

    wins = sum(1 for t in trades if t["won"])
    losses = len(trades) - wins

    for i, trade in enumerate(trades):
        result = "GANÓ" if trade["won"] else "PERDIÓ"
        change = history[i + 1] - history[i]
        sign = "+" if change >= 0 else ""
        print(f"  Trade {i + 1:>2}: {result}  |  "
              f"Bankroll: ${history[i + 1]:>7.2f}  ({sign}{change:.2f})")

    print()
    print(f"  Bankroll final:    ${history[-1]:.2f}")
    print(f"  Ganancia/Pérdida:  ${history[-1] - history[0]:+.2f} "
          f"({(history[-1] / history[0] - 1) * 100:+.1f}%)")
    print(f"  Trades ganados:    {wins}/{len(trades)} ({wins/len(trades)*100:.0f}%)")
    print()
    print("  Nota: El tamaño de cada apuesta se ajusta automáticamente")
    print("  al bankroll actual. Si pierdes, apuestas menos. Si ganas,")
    print("  apuestas más. Esto protege tu capital en rachas malas y")
    print("  acelera el crecimiento en rachas buenas.")
    print("=" * 60)
