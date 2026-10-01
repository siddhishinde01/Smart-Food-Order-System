"""
FoodTech Smart Delivery Assignment Engine
Recommends the most suitable delivery partner for an order.
"""


def score_partner(partner: dict, order: dict) -> float:
    """Score a delivery partner for a given order (higher = better match)."""
    if not partner.get("available"):
        return -1

    score = 100.0

    # Penalize by current order load
    score -= partner.get("current_orders", 0) * 20

    # Reward closer partners
    score -= partner.get("distance_from_hub_km", 5) * 5

    # Reward same-zone deliveries
    if partner.get("zone") == order.get("delivery_zone"):
        score += 15

    # Reward higher-rated partners
    score += (partner.get("rating", 4.0) - 4.0) * 10

    return score


def recommend_partner(order: dict, delivery_partners: list) -> dict:
    """
    Returns the best partner recommendation with reasoning.
    {
        partner: dict or None,
        reason: str,
        alternatives: list
    }
    """
    available = [p for p in delivery_partners if p.get("available")]

    if not available:
        return {
            "partner":      None,
            "reason":       "No delivery partners are currently available. Please wait for a partner to become free.",
            "alternatives": [],
        }

    scored = []
    for p in delivery_partners:
        s = score_partner(p, order)
        scored.append({"partner": p, "score": s})

    scored.sort(key=lambda x: x["score"], reverse=True)

    best = scored[0]
    partner = best["partner"]

    # Build explanation
    reasons = []
    if partner.get("current_orders", 0) == 0:
        reasons.append("currently free with no active orders")
    else:
        reasons.append(f"has only {partner['current_orders']} active order(s)")

    reasons.append(f"{partner['distance_from_hub_km']} km from restaurant hub")

    if partner.get("zone") == order.get("delivery_zone"):
        reasons.append(f"serves the same delivery zone ({order.get('delivery_zone')})")

    reasons.append(f"rated {partner.get('rating', 4.0)}/5.0 by customers")

    reason_text = (
        f"Recommended {partner['name']}: " + ", ".join(reasons) + "."
    )

    alternatives = [s["partner"] for s in scored[1:3] if s["score"] > 0]

    return {
        "partner":      partner,
        "reason":       reason_text,
        "alternatives": alternatives,
    }


def detect_batch_opportunities(orders: list) -> list:
    """
    Detect orders that could be batched based on nearby delivery zones.
    Returns list of batch groups.
    """
    active = [o for o in orders if o.get("status") in ("pending", "preparing") and not o.get("assigned_partner")]

    # Group by delivery zone
    zone_groups: dict = {}
    for o in active:
        zone = o.get("delivery_zone", "Unknown")
        zone_groups.setdefault(zone, []).append(o)

    batches = []
    for zone, group in zone_groups.items():
        if len(group) >= 2:
            # Further filter: only batch orders with similar distance (within 2 km)
            group.sort(key=lambda x: x.get("distance_km", 0))
            for i in range(len(group) - 1):
                o1, o2 = group[i], group[i + 1]
                if abs(o1.get("distance_km", 0) - o2.get("distance_km", 0)) <= 2.5:
                    batches.append({
                        "orders":    [o1["id"], o2["id"]],
                        "zone":      zone,
                        "customers": [o1["customer"], o2["customer"]],
                        "savings_km": round(max(o1["distance_km"], o2["distance_km"]) * 0.4, 1),
                        "reason":    f"Orders {o1['id']} and {o2['id']} are both delivering to {zone} zone "
                                     f"(within ~{abs(o1.get('distance_km',0)-o2.get('distance_km',0)):.1f} km of each other). "
                                     f"Batching could save ~{round(max(o1['distance_km'], o2['distance_km']) * 0.4, 1)} km of travel.",
                    })
    return batches
