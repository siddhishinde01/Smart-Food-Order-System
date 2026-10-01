"""
FoodTech AI Smart Priority Engine
Calculates a 0-100 priority score for each order based on multiple factors.
"""
from datetime import datetime


# ─── Weights (must sum to 1.0) ────────────────────────────────────────────────
WEIGHTS = {
    "waiting_time":       0.25,
    "prep_time":          0.20,
    "distance":           0.15,
    "restaurant_load":    0.20,
    "partner_scarcity":   0.10,
    "eta_risk":           0.10,
}

# Thresholds
MAX_WAITING_MIN   = 60    # normalize waiting time against 60 min max
MAX_PREP_MIN      = 35    # max prep time considered
MAX_DIST_KM       = 10    # max delivery distance considered
MAX_LOAD_PCT      = 100   # restaurant load %
ETA_RISK_WINDOW   = 45    # minutes — orders older than this become high risk


def _minutes_waiting(order: dict) -> float:
    placed = datetime.fromisoformat(order["placed_at"])
    return (datetime.now() - placed).total_seconds() / 60.0


def _restaurant_load_pct(restaurant: dict) -> float:
    cap = restaurant.get("max_capacity", 10)
    active = restaurant.get("active_orders", 0)
    return min((active / cap) * 100, 100)


def _partner_scarcity(delivery_partners: list) -> float:
    """0-100: 100 means no partners available (high risk)."""
    available = [p for p in delivery_partners if p.get("available") and p.get("current_orders", 0) < 2]
    total = len(delivery_partners)
    if total == 0:
        return 100
    shortage_ratio = 1 - (len(available) / total)
    return shortage_ratio * 100


def _eta_risk_score(order: dict, prep_time: int, distance_km: float) -> float:
    """
    Estimate whether the order will breach its implicit ~45-min delivery window.
    Returns 0–100 risk score.
    """
    waiting_min = _minutes_waiting(order)
    travel_time = distance_km * 3   # rough: 3 min per km
    total_estimated = waiting_min + prep_time + travel_time
    ratio = total_estimated / ETA_RISK_WINDOW
    return min(ratio * 80, 100)   # cap at 100


def _normalize(value: float, max_val: float) -> float:
    """Normalize a value to 0–1 range."""
    return min(value / max_val, 1.0)


def calculate_order_priority(order: dict, restaurant: dict, delivery_partners: list, prep_time: int) -> dict:
    """
    Returns a dict with:
      - score (0-100)
      - classification (CRITICAL / HIGH / NORMAL / LOW)
      - reasoning (list of human-readable strings)
      - factor_scores (breakdown dict)
    """
    waiting_min = _minutes_waiting(order)
    distance_km = order.get("distance_km", 3.0)
    rest_load   = _restaurant_load_pct(restaurant)
    partner_sc  = _partner_scarcity(delivery_partners)
    eta_risk    = _eta_risk_score(order, prep_time, distance_km)

    # Normalize each factor to 0–1
    f_waiting  = _normalize(waiting_min, MAX_WAITING_MIN)
    f_prep     = _normalize(prep_time,   MAX_PREP_MIN)
    f_distance = 1 - _normalize(distance_km, MAX_DIST_KM)   # closer = higher priority
    f_load     = _normalize(rest_load,   MAX_LOAD_PCT)
    f_scarcity = _normalize(partner_sc,  100)
    f_eta      = _normalize(eta_risk,    100)

    raw_score = (
        f_waiting  * WEIGHTS["waiting_time"]    +
        f_prep     * WEIGHTS["prep_time"]       +
        f_distance * WEIGHTS["distance"]        +
        f_load     * WEIGHTS["restaurant_load"] +
        f_scarcity * WEIGHTS["partner_scarcity"]+
        f_eta      * WEIGHTS["eta_risk"]
    )
    score = round(raw_score * 100)

    # Classification
    if score >= 80:
        classification = "CRITICAL"
    elif score >= 60:
        classification = "HIGH"
    elif score >= 35:
        classification = "NORMAL"
    else:
        classification = "LOW"

    # Human-readable reasoning
    reasoning = []

    if waiting_min > 30:
        reasoning.append(f"Customer has been waiting {waiting_min:.0f} minutes — urgency is high")
    elif waiting_min > 15:
        reasoning.append(f"Customer waiting time ({waiting_min:.0f} min) is above average")

    if prep_time >= 25:
        reasoning.append(f"High preparation time ({prep_time} min) increases delay risk")
    elif prep_time >= 15:
        reasoning.append(f"Moderate preparation time ({prep_time} min) requires timely dispatch")

    if distance_km <= 2.5:
        reasoning.append(f"Short delivery distance ({distance_km} km) — quick win to reduce queue")
    elif distance_km >= 5.0:
        reasoning.append(f"Long delivery distance ({distance_km} km) — must dispatch early")

    if rest_load >= 80:
        reasoning.append(f"Restaurant workload is critically high ({rest_load:.0f}%) — kitchen bottleneck risk")
    elif rest_load >= 60:
        reasoning.append(f"Restaurant load at {rest_load:.0f}% — moderate congestion")

    if partner_sc >= 70:
        reasoning.append("Very few delivery partners available — assign partner immediately")
    elif partner_sc >= 40:
        reasoning.append("Delivery partner scarcity is moderate — prioritize assignment")

    if eta_risk >= 80:
        reasoning.append("ETA breach is imminent — order is at serious risk of delay")
    elif eta_risk >= 50:
        reasoning.append("Delivery ETA is approaching threshold — action needed soon")

    if not reasoning:
        reasoning.append("Order is progressing normally with no immediate concerns")

    factor_scores = {
        "Waiting Time":        round(f_waiting  * 100),
        "Preparation Time":    round(f_prep     * 100),
        "Distance Factor":     round(f_distance * 100),
        "Restaurant Load":     round(f_load     * 100),
        "Partner Scarcity":    round(f_scarcity * 100),
        "ETA Risk":            round(f_eta      * 100),
    }

    return {
        "score":          score,
        "classification": classification,
        "reasoning":      reasoning,
        "factor_scores":  factor_scores,
        "metrics": {
            "waiting_min":  round(waiting_min, 1),
            "prep_time":    prep_time,
            "distance_km":  distance_km,
            "rest_load_pct": round(rest_load, 1),
        }
    }
