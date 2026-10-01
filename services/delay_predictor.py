"""
FoodTech Predictive Delay Monitor
Analyzes active orders and predicts which ones are likely to be delayed.
"""
from datetime import datetime

DELIVERY_PROMISE_MIN = 45   # promised delivery within this window
TRAVEL_SPEED_KM_PER_MIN = 0.33  # ~20 km/h average


def _minutes_waiting(order: dict) -> float:
    placed = datetime.fromisoformat(order["placed_at"])
    return (datetime.now() - placed).total_seconds() / 60.0


def predict_delay(order: dict, restaurant: dict, delivery_partners: list, prep_time: int) -> dict:
    """
    Returns delay prediction for a single order.
    {
        at_risk: bool,
        predicted_delay_min: int,    # extra minutes beyond promise
        risk_level: str,             # HIGH / MEDIUM / LOW / NONE
        reason: str,
        estimated_total_min: float,
    }
    """
    waiting_min   = _minutes_waiting(order)
    travel_min    = order.get("distance_km", 3.0) / TRAVEL_SPEED_KM_PER_MIN
    rest_load     = min((restaurant.get("active_orders", 0) / restaurant.get("max_capacity", 10)) * 100, 100)

    # Remaining prep time (assume half elapsed if status is 'preparing')
    status = order.get("status", "pending")
    if status == "pending":
        remaining_prep = prep_time
    elif status == "preparing":
        remaining_prep = max(prep_time - (waiting_min * 0.5), 2)
    else:
        remaining_prep = 0

    # Add kitchen congestion overhead
    congestion_overhead = (rest_load / 100) * 8   # up to 8 extra min at 100% load

    estimated_total = waiting_min + remaining_prep + travel_min + congestion_overhead
    predicted_delay = estimated_total - DELIVERY_PROMISE_MIN

    reasons = []

    if rest_load >= 80:
        reasons.append(f"Kitchen workload is critically high ({rest_load:.0f}%)")
    elif rest_load >= 60:
        reasons.append(f"Restaurant load at {rest_load:.0f}% causing slowdowns")

    if remaining_prep >= 20:
        reasons.append(f"Estimated prep time remaining: {remaining_prep:.0f} min")

    if travel_min >= 15:
        reasons.append(f"Delivery distance requires {travel_min:.0f} min travel")

    if waiting_min >= 25:
        reasons.append(f"Customer already waiting {waiting_min:.0f} min")

    if not order.get("assigned_partner"):
        reasons.append("No delivery partner assigned yet — dispatch pending")

    reason_text = "; ".join(reasons) if reasons else "Order progressing on schedule"

    if predicted_delay >= 15:
        risk_level = "HIGH"
        at_risk = True
    elif predicted_delay >= 8:
        risk_level = "MEDIUM"
        at_risk = True
    elif predicted_delay >= 3:
        risk_level = "LOW"
        at_risk = True
    else:
        risk_level = "NONE"
        at_risk = False

    return {
        "at_risk":              at_risk,
        "predicted_delay_min":  max(0, round(predicted_delay)),
        "risk_level":           risk_level,
        "reason":               reason_text,
        "estimated_total_min":  round(estimated_total, 1),
        "remaining_prep_min":   round(remaining_prep, 1),
        "travel_min":           round(travel_min, 1),
    }


def analyze_all_orders(orders: list, restaurants_dict: dict, delivery_partners: list, prep_times: dict) -> list:
    """Run delay prediction on all active (non-delivered) orders."""
    results = []
    for order in orders:
        if order.get("status") == "delivered":
            continue
        rest = restaurants_dict.get(order["restaurant_id"], {})
        prep  = prep_times.get(order["id"], 20)
        pred  = predict_delay(order, rest, delivery_partners, prep)
        results.append({
            "order_id":    order["id"],
            "customer":    order["customer"],
            "status":      order["status"],
            **pred
        })
    # Sort by risk — HIGH first
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}
    results.sort(key=lambda x: (risk_order.get(x["risk_level"], 4), -x["predicted_delay_min"]))
    return results
