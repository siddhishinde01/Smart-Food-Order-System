
"""
FoodTech — Smart Food Delivery Order Management Platform
Main Flask Application
"""

import copy
import os
import random
import sys
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Make the project root available for internal imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.sample_data import (
    RESTAURANTS,
    MENU_ITEMS,
    DELIVERY_PARTNERS,
    SEED_ORDERS,
    MENU_DICT,
    get_prep_time_for_order,
)

from services.priority_engine import calculate_order_priority
from services.delay_predictor import analyze_all_orders
from services.assignment_engine import (
    recommend_partner,
    detect_batch_opportunities,
)
from services.recommendation_engine import (
    generate_recommendations,
    simulate_what_if,
)


# ============================================================
# APP SETUP
# ============================================================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

CORS(app)


# ============================================================
# IN-MEMORY DATA
# ============================================================

orders = copy.deepcopy(SEED_ORDERS)
delivery_partners = copy.deepcopy(DELIVERY_PARTNERS)
restaurants = copy.deepcopy(RESTAURANTS)

carts = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _restaurants_dict():
    """Return restaurants indexed by restaurant ID."""
    return {restaurant["id"]: restaurant for restaurant in restaurants}


def _sync_restaurant_loads():
    """Update active order counts and restaurant load percentages."""
    for restaurant in restaurants:
        active_count = sum(
            1
            for order in orders
            if order["restaurant_id"] == restaurant["id"]
            and order["status"] != "delivered"
        )

        restaurant["active_orders"] = active_count

        capacity = restaurant.get("max_capacity", 1)
        restaurant["current_load"] = round(
            min((active_count / max(capacity, 1)) * 100, 100),
            1,
        )


def _get_prep_times():
    """Calculate food preparation time for every order."""
    return {
        order["id"]: get_prep_time_for_order(order, MENU_DICT)
        for order in orders
    }


def _enrich_orders():
    """Calculate priority scores and classifications for all orders."""
    _sync_restaurant_loads()

    restaurant_dict = _restaurants_dict()
    prep_times = _get_prep_times()

    for order in orders:
        restaurant = restaurant_dict.get(
            order["restaurant_id"], {}
        )

        prep_time = prep_times.get(order["id"], 20)

        result = calculate_order_priority(
            order,
            restaurant,
            delivery_partners,
            prep_time,
        )

        order["priority_score"] = result["score"]
        order["priority_class"] = result["classification"]
        order["priority_reasoning"] = result["reasoning"]
        order["priority_factors"] = result["factor_scores"]
        order["priority_metrics"] = result["metrics"]

    return orders


def _find_order(order_id):
    """Find an order by ID."""
    return next(
        (order for order in orders if order["id"] == order_id),
        None,
    )


def _get_json_data():
    """Safely retrieve JSON request data."""
    return request.get_json(silent=True) or {}


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template(
        "index.html",
        restaurants=restaurants,
    )


@app.route("/menu/<restaurant_id>")
def menu(restaurant_id):
    restaurant = next(
        (
            item for item in restaurants
            if item["id"] == restaurant_id
        ),
        None,
    )

    if not restaurant:
        return "Restaurant not found", 404

    items = [
        item for item in MENU_ITEMS
        if item["restaurant_id"] == restaurant_id
    ]

    return render_template(
        "menu.html",
        restaurant=restaurant,
        menu_items=items,
    )


@app.route("/cart")
def cart():
    return render_template(
        "cart.html",
        restaurants=restaurants,
        menu_items=MENU_ITEMS,
    )


@app.route("/checkout")
def checkout():
    return render_template("checkout.html")


@app.route("/order-confirmation/<order_id>")
def order_confirmation(order_id):
    order = _find_order(order_id)

    if not order:
        return "Order not found", 404

    restaurant = _restaurants_dict().get(
        order["restaurant_id"], {}
    )

    return render_template(
        "order_confirmation.html",
        order=order,
        restaurant=restaurant,
    )


@app.route("/tracking/<order_id>")
def tracking(order_id):
    order = _find_order(order_id)

    if not order:
        return "Order not found", 404

    return render_template(
        "tracking.html",
        order=order,
    )


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ============================================================
# API — ORDERS
# ============================================================

@app.route("/api/orders", methods=["GET"])
def api_orders():
    _enrich_orders()

    restaurant_dict = _restaurants_dict()
    prep_times = _get_prep_times()
    result = []

    for order in orders:
        restaurant = restaurant_dict.get(
            order["restaurant_id"], {}
        )

        partner = next(
            (
                item for item in delivery_partners
                if item["id"] == order.get("assigned_partner")
            ),
            None,
        )

        result.append({
            **order,
            "restaurant_name": restaurant.get("name", ""),
            "restaurant_zone": restaurant.get("zone", ""),
            "prep_time": prep_times.get(order["id"], 20),
            "partner_name": partner["name"] if partner else None,
        })

    result.sort(
        key=lambda item: item.get("priority_score", 0) or 0,
        reverse=True,
    )

    return jsonify(result)


@app.route("/api/orders", methods=["POST"])
def api_create_order():
    data = _get_json_data()

    raw_items = data.get("items", [])

    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({
            "success": False,
            "error": "At least one valid order item is required.",
        }), 400

    formatted_items = []

    try:
        for item in raw_items:
            if not isinstance(item, dict):
                continue

            menu_id = item.get("menu_id") or item.get("id") or "M1"
            name = item.get("name") or "Food Item"
            quantity = int(item.get("qty") or 1)
            price = float(item.get("price") or 0)

            if quantity < 1 or price < 0:
                return jsonify({
                    "success": False,
                    "error": "Quantity must be positive and price cannot be negative.",
                }), 400

            formatted_items.append({
                "menu_id": menu_id,
                "id": menu_id,
                "name": name,
                "qty": quantity,
                "price": price,
            })

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid quantity or price.",
        }), 400

    if not formatted_items:
        return jsonify({
            "success": False,
            "error": "No valid order items were provided.",
        }), 400

    restaurant_id = data.get("restaurant_id")

    if not restaurant_id and restaurants:
        restaurant_id = restaurants[0]["id"]

    if not any(
        restaurant["id"] == restaurant_id
        for restaurant in restaurants
    ):
        return jsonify({
            "success": False,
            "error": "Restaurant not found.",
        }), 404

    try:
        total = float(data.get("total") or 0)

        if total < 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid order total.",
        }), 400

    order_id = f"ORD-{random.randint(200, 999)}"

    while any(order["id"] == order_id for order in orders):
        order_id = f"ORD-{random.randint(200, 999)}"

    new_order = {
        "id": order_id,
        "customer": data.get("customer_name") or "New Customer",
        "customer_phone": data.get("phone", ""),
        "restaurant_id": restaurant_id,
        "items": formatted_items,
        "total": total,
        "status": "pending",
        "delivery_zone": data.get("delivery_zone") or "Central",
        "distance_km": round(random.uniform(1.5, 7.0), 1),
        "placed_at": datetime.now().isoformat(),
        "assigned_partner": None,
        "priority_score": None,
        "notes": data.get("notes", ""),
    }

    orders.append(new_order)
    _sync_restaurant_loads()

    return jsonify({
        "success": True,
        "order_id": order_id,
        "order": new_order,
    }), 201


@app.route("/api/orders/<order_id>", methods=["GET"])
def api_order_detail(order_id):
    _enrich_orders()

    order = _find_order(order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    restaurant = _restaurants_dict().get(
        order["restaurant_id"], {}
    )

    prep_time = get_prep_time_for_order(order, MENU_DICT)
    assignment = recommend_partner(order, delivery_partners)

    partner = next(
        (
            item for item in delivery_partners
            if item["id"] == order.get("assigned_partner")
        ),
        None,
    )

    return jsonify({
        **order,
        "restaurant_name": restaurant.get("name", ""),
        "prep_time": prep_time,
        "partner_name": partner["name"] if partner else None,
        "partner_recommendation": {
            "partner": assignment["partner"],
            "reason": assignment["reason"],
            "alternatives": assignment["alternatives"],
        },
    })


@app.route("/api/orders/<order_id>/status", methods=["PATCH"])
def api_update_status(order_id):
    order = _find_order(order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = _get_json_data()
    new_status = data.get("status")

    allowed_statuses = {
        "pending",
        "preparing",
        "out_for_delivery",
        "delivered",
    }

    if new_status not in allowed_statuses:
        return jsonify({
            "success": False,
            "error": "Invalid order status.",
        }), 400

    order["status"] = new_status
    _sync_restaurant_loads()

    return jsonify({
        "success": True,
        "status": order["status"],
    })


@app.route("/api/orders/<order_id>/assign", methods=["POST"])
def api_assign_partner(order_id):
    order = _find_order(order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = _get_json_data()
    partner_id = data.get("partner_id")

    partner = next(
        (
            item for item in delivery_partners
            if item["id"] == partner_id
        ),
        None,
    )

    if not partner:
        return jsonify({"error": "Partner not found"}), 404

    previous_partner_id = order.get("assigned_partner")

    # Avoid counting the same assignment twice.
    if previous_partner_id == partner_id:
        return jsonify({
            "success": True,
            "message": "Partner is already assigned.",
        })

    # Release the previous partner, if present.
    if previous_partner_id:
        previous_partner = next(
            (
                item for item in delivery_partners
                if item["id"] == previous_partner_id
            ),
            None,
        )

        if previous_partner:
            previous_partner["current_orders"] = max(
                0,
                previous_partner.get("current_orders", 0) - 1,
            )

            previous_partner["available"] = (
                previous_partner["current_orders"] < 2
            )

    # Assign the new partner.
    partner["current_orders"] = (
        partner.get("current_orders", 0) + 1
    )

    partner["available"] = partner["current_orders"] < 2
    order["assigned_partner"] = partner_id

    return jsonify({
        "success": True,
        "partner_id": partner_id,
    })


# ============================================================
# API — DASHBOARD SUMMARY
# ============================================================

@app.route("/api/dashboard/summary", methods=["GET"])
def api_dashboard_summary():
    _enrich_orders()
    _sync_restaurant_loads()

    active_orders = [
        order for order in orders
        if order["status"] != "delivered"
    ]

    at_risk_orders = [
        order for order in active_orders
        if order.get("priority_class") in ("CRITICAL", "HIGH")
    ]

    available_partners = [
        partner for partner in delivery_partners
        if partner.get("available")
        and partner.get("current_orders", 0) < 2
    ]

    estimated_times = []

    for order in active_orders:
        prep_time = get_prep_time_for_order(order, MENU_DICT)
        travel_time = order.get("distance_km", 3) * 3

        estimated_times.append(prep_time + travel_time)

    average_eta = (
        round(sum(estimated_times) / len(estimated_times), 1)
        if estimated_times else 0
    )

    restaurant_loads = [
        restaurant["current_load"]
        for restaurant in restaurants
    ]

    average_load = (
        round(sum(restaurant_loads) / len(restaurant_loads), 1)
        if restaurant_loads else 0
    )

    delivered_count = sum(
        1 for order in orders
        if order["status"] == "delivered"
    )

    return jsonify({
        "active_orders": len(active_orders),
        "at_risk_orders": len(at_risk_orders),
        "avg_eta_min": average_eta,
        "available_partners": len(available_partners),
        "total_partners": len(delivery_partners),
        "avg_restaurant_load": average_load,
        "total_orders_today": len(orders),
        "delivered_today": delivered_count,
        "restaurants": [
            {
                "id": restaurant["id"],
                "name": restaurant["name"],
                "load": restaurant["current_load"],
                "active": restaurant["active_orders"],
            }
            for restaurant in restaurants
        ],
    })


# ============================================================
# API — DELAY PREDICTIONS
# ============================================================

@app.route("/api/dashboard/delay-predictions", methods=["GET"])
def api_delay_predictions():
    _enrich_orders()
    _sync_restaurant_loads()

    prep_times = _get_prep_times()

    results = analyze_all_orders(
        orders,
        _restaurants_dict(),
        delivery_partners,
        prep_times,
    )

    return jsonify(results)


# ============================================================
# API — RECOMMENDATIONS
# ============================================================

@app.route("/api/dashboard/recommendations", methods=["GET"])
def api_recommendations():
    _enrich_orders()
    _sync_restaurant_loads()

    prep_times = _get_prep_times()

    priority_results = [
        {
            "order_id": order["id"],
            "score": order.get("priority_score", 0),
            "classification": order.get(
                "priority_class", "NORMAL"
            ),
            "reasoning": order.get("priority_reasoning", []),
        }
        for order in orders
    ]

    delay_results = analyze_all_orders(
        orders,
        _restaurants_dict(),
        delivery_partners,
        prep_times,
    )

    recommendations = generate_recommendations(
        orders,
        _restaurants_dict(),
        delivery_partners,
        priority_results,
        delay_results,
    )

    return jsonify(recommendations)


# ============================================================
# API — DELIVERY BATCHING
# ============================================================

@app.route("/api/dashboard/batching", methods=["GET"])
def api_batching():
    batches = detect_batch_opportunities(orders)
    return jsonify(batches)


# ============================================================
# API — WHAT-IF SIMULATION
# ============================================================

@app.route("/api/simulate/what-if", methods=["POST"])
def api_what_if():
    data = _get_json_data()

    try:
        extra_orders = int(data.get("extra_orders", 5))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "extra_orders must be an integer.",
        }), 400

    extra_orders = max(1, min(extra_orders, 20))

    result = simulate_what_if(
        orders,
        _restaurants_dict(),
        delivery_partners,
        extra_orders,
    )

    return jsonify(result)


# ============================================================
# API — DELIVERY PARTNERS
# ============================================================

@app.route("/api/partners", methods=["GET"])
def api_partners():
    return jsonify(delivery_partners)


# ============================================================
# API — RESTAURANTS
# ============================================================

@app.route("/api/restaurants", methods=["GET"])
def api_restaurants():
    _sync_restaurant_loads()
    return jsonify(restaurants)


# ============================================================
# API — MENU
# ============================================================

@app.route("/api/menu", methods=["GET"])
def api_menu():
    restaurant_id = request.args.get("restaurant_id")

    if restaurant_id:
        items = [
            item for item in MENU_ITEMS
            if item["restaurant_id"] == restaurant_id
        ]
        return jsonify(items)

    return jsonify(MENU_ITEMS)


# ============================================================
# API — PARTNER RECOMMENDATION
# ============================================================

@app.route(
    "/api/recommend-partner/<order_id>",
    methods=["GET"],
)
def api_recommend_partner(order_id):
    order = _find_order(order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    recommendation = recommend_partner(
        order,
        delivery_partners,
    )

    return jsonify(recommendation)


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))

    print(f"FoodTech starting on http://{host}:{port}")

    app.run(
        debug=True,
        host=host,
        port=port,
    )