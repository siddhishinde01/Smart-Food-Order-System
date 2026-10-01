"""
FoodTech AI Recommendation Engine
Generates actionable recommendations from live order data.
"""
from datetime import datetime


def _minutes_waiting(order: dict) -> float:
    placed = datetime.fromisoformat(order["placed_at"])
    return (datetime.now() - placed).total_seconds() / 60.0


def generate_recommendations(orders: list, restaurants_dict: dict, delivery_partners: list,
                              priority_results: list, delay_results: list) -> list:
    """
    Generate a ranked list of AI recommendations.
    Each recommendation: { type, priority, title, description, order_id (opt), partner_id (opt) }
    """
    recs = []
    priority_map = {p["order_id"]: p for p in priority_results}
    delay_map    = {d["order_id"]: d for d in delay_results}

    # 1. Critical/High priority orders that need immediate action
    critical_orders = [p for p in priority_results if p["classification"] in ("CRITICAL", "HIGH")
                       and _get_status(p["order_id"], orders) in ("pending", "preparing")]
    if critical_orders:
        top = critical_orders[0]
        recs.append({
            "type":        "URGENT_PREPARE",
            "priority":    "CRITICAL",
            "icon":        "🔥",
            "title":       f"Prioritize {top['order_id']} Next",
            "description": f"Move {top['order_id']} to the top of the preparation queue. "
                           f"Priority score: {top['score']}/100. {top['reasoning'][0] if top.get('reasoning') else ''}",
            "order_id":    top["order_id"],
        })

    # 2. Unassigned orders with high risk
    unassigned = [o for o in orders
                  if not o.get("assigned_partner")
                  and o.get("status") in ("pending", "preparing")]
    available_partners = [p for p in delivery_partners if p.get("available") and p.get("current_orders", 0) < 2]

    if unassigned and available_partners:
        best_partner = min(available_partners, key=lambda p: p.get("distance_from_hub_km", 99))
        urgent_unassigned = sorted(unassigned, key=lambda o: priority_map.get(o["id"], {}).get("score", 0), reverse=True)
        if urgent_unassigned:
            target = urgent_unassigned[0]
            recs.append({
                "type":       "ASSIGN_PARTNER",
                "priority":   "HIGH",
                "icon":       "🛵",
                "title":      f"Assign {best_partner['name']} → {target['id']}",
                "description": f"Assign {best_partner['name']} to {target['id']} ({target['customer']}). "
                               f"{best_partner['name']} is available and closest to the restaurant hub "
                               f"({best_partner['distance_from_hub_km']} km away).",
                "order_id":   target["id"],
                "partner_id": best_partner["id"],
            })

    # 3. At-risk orders
    high_risk = [d for d in delay_results if d["risk_level"] == "HIGH"]
    if high_risk:
        r = high_risk[0]
        recs.append({
            "type":       "DELAY_ALERT",
            "priority":   "HIGH",
            "icon":       "⚠️",
            "title":      f"{r['order_id']} is at HIGH delay risk",
            "description": f"Predicted delay of {r['predicted_delay_min']} min. {r['reason']}. "
                           f"Immediate action required to avoid SLA breach.",
            "order_id":   r["order_id"],
        })

    # 4. Restaurant overload
    for rest in restaurants_dict.values():
        load = min((rest.get("active_orders", 0) / rest.get("max_capacity", 10)) * 100, 100)
        if load >= 80:
            recs.append({
                "type":       "KITCHEN_ALERT",
                "priority":   "MEDIUM",
                "icon":       "🏪",
                "title":      f"{rest['name']} kitchen overloaded ({load:.0f}%)",
                "description": f"{rest['name']} is at {load:.0f}% capacity. "
                               f"Consider opening an additional preparation station to prevent cascading delays.",
                "order_id":   None,
            })

    # 5. Partner scarcity
    avail_count = len([p for p in delivery_partners if p.get("available") and p.get("current_orders",0) < 2])
    if avail_count <= 1:
        recs.append({
            "type":       "PARTNER_SHORTAGE",
            "priority":   "MEDIUM",
            "icon":       "🚨",
            "title":      "Critical delivery partner shortage",
            "description": f"Only {avail_count} partner(s) available. "
                           "Contact backup delivery partners or reduce new order acceptance temporarily.",
            "order_id":   None,
        })

    # 6. Long-waiting orders
    old_orders = [o for o in orders if _minutes_waiting(o) > 35 and o.get("status") != "delivered"]
    if old_orders:
        recs.append({
            "type":       "LONG_WAIT",
            "priority":   "MEDIUM",
            "icon":       "⏰",
            "title":      f"{len(old_orders)} order(s) waiting over 35 minutes",
            "description": f"Orders {', '.join(o['id'] for o in old_orders[:3])} have been waiting a long time. "
                           "Consider proactive customer notification and expedited handling.",
            "order_id":   old_orders[0]["id"] if old_orders else None,
        })

    # Sort by priority
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    recs.sort(key=lambda r: priority_order.get(r["priority"], 4))

    return recs[:6]   # Return top 6 recommendations


def _get_status(order_id: str, orders: list) -> str:
    for o in orders:
        if o["id"] == order_id:
            return o.get("status", "unknown")
    return "unknown"


def simulate_what_if(orders: list, restaurants_dict: dict, delivery_partners: list,
                     extra_orders: int = 5) -> dict:
    """
    Simulate what happens if `extra_orders` new orders arrive.
    Returns before/after comparison.
    """
    active = [o for o in orders if o.get("status") not in ("delivered",)]

    # ── BEFORE ────────────────────────────────────────────────────────────────
    before_count      = len(active)
    before_avail      = len([p for p in delivery_partners if p.get("available")])
    before_load       = _avg_load(restaurants_dict)
    before_at_risk    = _estimate_at_risk(active, restaurants_dict)
    before_avg_eta    = _estimate_avg_eta(active)

    # ── AFTER (simulate) ──────────────────────────────────────────────────────
    after_count   = before_count + extra_orders
    after_avail   = max(before_avail - 2, 0)   # partners get busy
    after_load    = min(before_load + (extra_orders * 5), 100)
    after_at_risk = min(before_at_risk + extra_orders - 1, after_count - 1)
    after_avg_eta = before_avg_eta + (extra_orders * 1.8)

    # AI recommendations for the surge
    if extra_orders >= 5:
        action = (
            f"Assign {max(2, extra_orders // 3)} additional delivery partners immediately. "
            f"Prioritize orders with high preparation time to clear kitchen capacity. "
            f"Consider temporarily halting new order acceptance until restaurant load drops below 80%."
        )
    else:
        action = (
            "Reassign available delivery partners to high-priority orders. "
            "Alert kitchen staff to expedite pending orders."
        )

    return {
        "before": {
            "active_orders":    before_count,
            "available_partners": before_avail,
            "restaurant_load":  round(before_load, 1),
            "at_risk_orders":   before_at_risk,
            "avg_eta_min":      round(before_avg_eta, 1),
        },
        "after": {
            "active_orders":    after_count,
            "available_partners": after_avail,
            "restaurant_load":  round(after_load, 1),
            "at_risk_orders":   after_at_risk,
            "avg_eta_min":      round(after_avg_eta, 1),
        },
        "extra_orders":    extra_orders,
        "ai_action":       action,
        "surge_level":     "CRITICAL" if after_load >= 90 else "HIGH" if after_load >= 75 else "MEDIUM",
    }


def _avg_load(restaurants_dict: dict) -> float:
    if not restaurants_dict:
        return 0
    loads = []
    for r in restaurants_dict.values():
        cap = r.get("max_capacity", 10)
        act = r.get("active_orders", 0)
        loads.append(min((act / cap) * 100, 100))
    return sum(loads) / len(loads)


def _estimate_at_risk(orders: list, restaurants_dict: dict) -> int:
    count = 0
    from datetime import datetime
    for o in orders:
        placed = datetime.fromisoformat(o["placed_at"])
        wait = (datetime.now() - placed).total_seconds() / 60
        if wait > 25 or o.get("distance_km", 0) > 4.5:
            count += 1
    return count


def _estimate_avg_eta(orders: list) -> float:
    if not orders:
        return 0
    etas = []
    from datetime import datetime
    for o in orders:
        placed = datetime.fromisoformat(o["placed_at"])
        wait = (datetime.now() - placed).total_seconds() / 60
        travel = o.get("distance_km", 3) * 3
        etas.append(wait + travel + 10)  # 10 min prep assumption
    return sum(etas) / len(etas)
