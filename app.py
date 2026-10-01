"""
FoodTech — Smart Food Delivery Order Management Platform
Main Flask Application
"""
import copy
import json
import random
import uuid
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# ── Internal Services ──────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from data.sample_data import (
    RESTAURANTS, MENU_ITEMS, DELIVERY_PARTNERS, SEED_ORDERS,
    MENU_DICT, get_prep_time_for_order
)
from services.priority_engine     import calculate_order_priority
from services.delay_predictor     import analyze_all_orders
from services.assignment_engine   import recommend_partner, detect_batch_opportunities
from services.recommendation_engine import generate_recommendations, simulate_what_if

# ── App Setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ── In-Memory State ────────────────────────────────────────────────────────────
orders            = copy.deepcopy(SEED_ORDERS)
delivery_partners = copy.deepcopy(DELIVERY_PARTNERS)
restaurants       = copy.deepcopy(RESTAURANTS)
carts             = {}   # session_id -> list of cart items


def _restaurants_dict():
    return {r["id"]: r for r in restaurants}


def _sync_restaurant_loads():
    """Recompute active_orders count for each restaurant."""
    for r in restaurants:
        r["active_orders"] = sum(
            1 for o in orders
            if o["restaurant_id"] == r["id"] and o["status"] not in ("delivered",)
        )
        r["current_load"] = round(
            min((r["active_orders"] / r["max_capacity"]) * 100, 100), 1
        )


def _get_prep_times():
    return {o["id"]: get_prep_time_for_order(o, MENU_DICT) for o in orders}


def _enrich_orders():
    """Attach priority, delay, and partner recommendation to every order."""
    _sync_restaurant_loads()
    rdict     = _restaurants_dict()
    prep_times = _get_prep_times()

    for o in orders:
        rest   = rdict.get(o["restaurant_id"], {})
        prep   = prep_times.get(o["id"], 20)
        result = calculate_order_priority(o, rest, delivery_partners, prep)
        o["priority_score"]      = result["score"]
        o["priority_class"]      = result["classification"]
        o["priority_reasoning"]  = result["reasoning"]
        o["priority_factors"]    = result["factor_scores"]
        o["priority_metrics"]    = result["metrics"]

    return orders


# ─────────────────────────────────────────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", restaurants=restaurants)


@app.route("/menu/<restaurant_id>")
def menu(restaurant_id):
    rest = next((r for r in restaurants if r["id"] == restaurant_id), None)
    if not rest:
        return "Restaurant not found", 404
    items = [m for m in MENU_ITEMS if m["restaurant_id"] == restaurant_id]
    return render_template("menu.html", restaurant=rest, menu_items=items)


@app.route("/cart")
def cart():
    return render_template("cart.html", restaurants=restaurants, menu_items=MENU_ITEMS)


@app.route("/checkout")
def checkout():
    return render_template("checkout.html")


@app.route("/order-confirmation/<order_id>")
def order_confirmation(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return "Order not found", 404
    rest = next((r for r in restaurants if r["id"] == order["restaurant_id"]), {})
    return render_template("order_confirmation.html", order=order, restaurant=rest)


@app.route("/tracking/<order_id>")
def tracking(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return "Order not found", 404
    return render_template("tracking.html", order=order)


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ─────────────────────────────────────────────────────────────────────────────
# API — ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/orders", methods=["GET"])
def api_orders():
    _enrich_orders()
    result = []
    rdict  = _restaurants_dict()
    prep_times = _get_prep_times()
    for o in orders:
        rest = rdict.get(o["restaurant_id"], {})
        partner = next((p for p in delivery_partners if p["id"] == o.get("assigned_partner")), None)
        result.append({
            **o,
            "restaurant_name": rest.get("name", ""),
            "restaurant_zone": rest.get("zone", ""),
            "prep_time":        prep_times.get(o["id"], 20),
            "partner_name":     partner["name"] if partner else None,
        })
    result.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return jsonify(result)


@app.route("/api/orders", methods=["POST"])
def api_create_order():
    data = request.get_json(silent=True) or {}
    order_id = f"ORD-{random.randint(200, 999)}"
    while any(o["id"] == order_id for o in orders):
        order_id = f"ORD-{random.randint(200, 999)}"

    # Format items to guarantee menu_id, id, name, qty, price keys exist
    raw_items = data.get("items", [])
    formatted_items = []
    for item in raw_items:
        if isinstance(item, dict):
            mid = item.get("menu_id") or item.get("id") or "M1"
            name = item.get("name") or "Food Item"
            qty = int(item.get("qty") or 1)
            price = float(item.get("price") or 0)
            formatted_items.append({
                "menu_id": mid,
                "id": mid,
                "name": name,
                "qty": qty,
                "price": price
            })

    rest_id = data.get("restaurant_id")
    if not rest_id and restaurants:
        rest_id = restaurants[0]["id"]

    new_order = {
        "id":              order_id,
        "customer":        data.get("customer_name") or "New Customer",
        "customer_phone":  data.get("phone", ""),
        "restaurant_id":   rest_id,
        "items":           formatted_items,
        "total":           float(data.get("total") or 0),
        "status":          "pending",
        "delivery_zone":   data.get("delivery_zone") or "Central",
        "distance_km":     round(random.uniform(1.5, 7.0), 1),
        "placed_at":       datetime.now().isoformat(),
        "assigned_partner": None,
        "priority_score":  None,
        "notes":           data.get("notes", ""),
    }
    orders.append(new_order)
    _sync_restaurant_loads()
    return jsonify({"success": True, "order_id": order_id, "order": new_order}), 201


@app.route("/api/orders/<order_id>", methods=["GET"])
def api_order_detail(order_id):
    _enrich_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    rdict  = _restaurants_dict()
    rest   = rdict.get(order["restaurant_id"], {})
    prep   = get_prep_time_for_order(order, MENU_DICT)
    assign = recommend_partner(order, delivery_partners)
    partner = next((p for p in delivery_partners if p["id"] == order.get("assigned_partner")), None)

    return jsonify({
        **order,
        "restaurant_name":  rest.get("name", ""),
        "prep_time":         prep,
        "partner_name":      partner["name"] if partner else None,
        "partner_recommendation": {
            "partner":      assign["partner"],
            "reason":       assign["reason"],
            "alternatives": assign["alternatives"],
        },
    })


@app.route("/api/orders/<order_id>/status", methods=["PATCH"])
def api_update_status(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return jsonify({"error": "Not found"}), 404
    new_status = request.json.get("status")
    if new_status in ("pending", "preparing", "out_for_delivery", "delivered"):
        order["status"] = new_status
    _sync_restaurant_loads()
    return jsonify({"success": True, "status": order["status"]})


@app.route("/api/orders/<order_id>/assign", methods=["POST"])
def api_assign_partner(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return jsonify({"error": "Not found"}), 404
    partner_id = request.json.get("partner_id")
    partner = next((p for p in delivery_partners if p["id"] == partner_id), None)
    if not partner:
        return jsonify({"error": "Partner not found"}), 404
    # Unassign previous
    if order.get("assigned_partner"):
        prev = next((p for p in delivery_partners if p["id"] == order["assigned_partner"]), None)
        if prev:
            prev["current_orders"] = max(0, prev["current_orders"] - 1)
            prev["available"] = prev["current_orders"] < 2
    order["assigned_partner"] = partner_id
    partner["current_orders"] += 1
    partner["available"] = partner["current_orders"] < 2
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────────────────────
# API — DASHBOARD INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/dashboard/summary")
def api_dashboard_summary():
    _enrich_orders()
    _sync_restaurant_loads()

    active = [o for o in orders if o["status"] not in ("delivered",)]
    at_risk_orders = [o for o in active if o.get("priority_class") in ("CRITICAL", "HIGH")]
    available_partners = [p for p in delivery_partners if p.get("available") and p.get("current_orders", 0) < 2]

    etas = []
    for o in active:
        prep  = get_prep_time_for_order(o, MENU_DICT)
        travel = o.get("distance_km", 3) * 3
        etas.append(prep + travel)
    avg_eta = round(sum(etas) / len(etas), 1) if etas else 0

    rest_loads = [r["current_load"] for r in restaurants]
    avg_load = round(sum(rest_loads) / len(rest_loads), 1) if rest_loads else 0

    return jsonify({
        "active_orders":         len(active),
        "at_risk_orders":        len(at_risk_orders),
        "avg_eta_min":           avg_eta,
        "available_partners":    len(available_partners),
        "total_partners":        len(delivery_partners),
        "avg_restaurant_load":   avg_load,
        "total_orders_today":    len(orders),
        "delivered_today":       len([o for o in orders if o["status"] == "delivered"]),
        "restaurants":           [{"id": r["id"], "name": r["name"], "load": r["current_load"], "active": r["active_orders"]} for r in restaurants],
    })


@app.route("/api/dashboard/delay-predictions")
def api_delay_predictions():
    _enrich_orders()
    _sync_restaurant_loads()
    prep_times = _get_prep_times()
    results = analyze_all_orders(orders, _restaurants_dict(), delivery_partners, prep_times)
    return jsonify(results)


@app.route("/api/dashboard/recommendations")
def api_recommendations():
    _enrich_orders()
    _sync_restaurant_loads()
    prep_times = _get_prep_times()

    priority_results = [{"order_id": o["id"], "score": o.get("priority_score", 0),
                         "classification": o.get("priority_class", "NORMAL"),
                         "reasoning": o.get("priority_reasoning", [])} for o in orders]
    delay_results = analyze_all_orders(orders, _restaurants_dict(), delivery_partners, prep_times)

    recs = generate_recommendations(orders, _restaurants_dict(), delivery_partners,
                                    priority_results, delay_results)
    return jsonify(recs)


@app.route("/api/dashboard/batching")
def api_batching():
    batches = detect_batch_opportunities(orders)
    return jsonify(batches)


@app.route("/api/simulate/what-if", methods=["POST"])
def api_what_if():
    data = request.json or {}
    extra = int(data.get("extra_orders", 5))
    extra = max(1, min(extra, 20))
    result = simulate_what_if(orders, _restaurants_dict(), delivery_partners, extra)
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────────────────
# API — PARTNERS / RESTAURANTS / MENU
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/partners")
def api_partners():
    return jsonify(delivery_partners)


@app.route("/api/restaurants")
def api_restaurants():
    _sync_restaurant_loads()
    return jsonify(restaurants)


@app.route("/api/menu")
def api_menu():
    rid = request.args.get("restaurant_id")
    if rid:
        return jsonify([m for m in MENU_ITEMS if m["restaurant_id"] == rid])
    return jsonify(MENU_ITEMS)


@app.route("/api/recommend-partner/<order_id>")
def api_recommend_partner(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return jsonify({"error": "Not found"}), 404
    rec = recommend_partner(order, delivery_partners)
    return jsonify(rec)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    print(f"FoodTech starting on http://{host}:{port}")
    app.run(debug=True, host=host, port=port)
