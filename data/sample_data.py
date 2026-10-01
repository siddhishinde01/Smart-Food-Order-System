import time
import random
from datetime import datetime, timedelta

# ── Restaurants ──────────────────────────────────────────────────────────────
RESTAURANTS = [
    {
        "id": "R1",
        "name": "Spice Garden",
        "cuisine": "Indian",
        "rating": 4.5,
        "prep_base_time": 18,   # minutes
        "current_load": 0,       # % – set dynamically
        "max_capacity": 10,
        "active_orders": 0,
        "zone": "North",
        "image": "🍛",
    },
    {
        "id": "R2",
        "name": "Burger Barn",
        "cuisine": "American",
        "rating": 4.2,
        "prep_base_time": 12,
        "current_load": 0,
        "max_capacity": 12,
        "active_orders": 0,
        "zone": "Central",
        "image": "🍔",
    },
    {
        "id": "R3",
        "name": "Sushi Zen",
        "cuisine": "Japanese",
        "rating": 4.7,
        "prep_base_time": 22,
        "current_load": 0,
        "max_capacity": 8,
        "active_orders": 0,
        "zone": "South",
        "image": "🍣",
    },
]

# ── Menu ──────────────────────────────────────────────────────────────────────
MENU_ITEMS = [
    # Spice Garden
    {"id": "M1", "restaurant_id": "R1", "name": "Butter Chicken", "price": 299, "prep_time": 20, "category": "Main", "description": "Creamy tomato-based curry with tender chicken", "emoji": "🍛", "rating": 4.6, "calories": 520},
    {"id": "M2", "restaurant_id": "R1", "name": "Paneer Tikka", "price": 249, "prep_time": 15, "category": "Starter", "description": "Grilled cottage cheese with spiced marinade", "emoji": "🧀", "rating": 4.4, "calories": 340},
    {"id": "M3", "restaurant_id": "R1", "name": "Dal Makhani", "price": 199, "prep_time": 18, "category": "Main", "description": "Slow-cooked black lentils with butter and cream", "emoji": "🫘", "rating": 4.5, "calories": 430},
    {"id": "M4", "restaurant_id": "R1", "name": "Garlic Naan", "price": 49, "prep_time": 8, "category": "Bread", "description": "Soft leavened bread baked in tandoor", "emoji": "🫓", "rating": 4.3, "calories": 180},
    # Burger Barn
    {"id": "M5", "restaurant_id": "R2", "name": "Classic Smash Burger", "price": 249, "prep_time": 10, "category": "Burger", "description": "Double smash patty with cheddar and special sauce", "emoji": "🍔", "rating": 4.5, "calories": 680},
    {"id": "M6", "restaurant_id": "R2", "name": "BBQ Chicken Burger", "price": 279, "prep_time": 12, "category": "Burger", "description": "Crispy chicken with smoky BBQ sauce and coleslaw", "emoji": "🍗", "rating": 4.3, "calories": 590},
    {"id": "M7", "restaurant_id": "R2", "name": "Loaded Fries", "price": 149, "prep_time": 8, "category": "Sides", "description": "Crispy fries with cheese sauce, jalapeños and bacon bits", "emoji": "🍟", "rating": 4.4, "calories": 450},
    {"id": "M8", "restaurant_id": "R2", "name": "Milkshake", "price": 119, "prep_time": 5, "category": "Beverages", "description": "Thick creamy milkshake — chocolate, vanilla or strawberry", "emoji": "🥤", "rating": 4.6, "calories": 380},
    # Sushi Zen
    {"id": "M9",  "restaurant_id": "R3", "name": "Dragon Roll", "price": 499, "prep_time": 25, "category": "Roll", "description": "Shrimp tempura topped with avocado and eel sauce", "emoji": "🍣", "rating": 4.8, "calories": 420},
    {"id": "M10", "restaurant_id": "R3", "name": "Salmon Sashimi", "price": 599, "prep_time": 20, "category": "Sashimi", "description": "Fresh premium salmon, 8 pieces", "emoji": "🐟", "rating": 4.9, "calories": 280},
    {"id": "M11", "restaurant_id": "R3", "name": "Miso Ramen", "price": 349, "prep_time": 22, "category": "Noodles", "description": "Rich miso broth with pork belly, egg and nori", "emoji": "🍜", "rating": 4.7, "calories": 560},
    {"id": "M12", "restaurant_id": "R3", "name": "Edamame", "price": 99, "prep_time": 5, "category": "Starter", "description": "Steamed salted soybeans", "emoji": "🫛", "rating": 4.2, "calories": 120},
]

# ── Delivery Partners ─────────────────────────────────────────────────────────
DELIVERY_PARTNERS = [
    {"id": "D1", "name": "Arjun Singh",    "zone": "North",   "available": True,  "current_orders": 0, "distance_from_hub_km": 1.2, "rating": 4.8, "completed_today": 12, "emoji": "🏍️"},
    {"id": "D2", "name": "Priya Sharma",   "zone": "Central", "available": True,  "current_orders": 1, "distance_from_hub_km": 2.5, "rating": 4.6, "completed_today": 9,  "emoji": "🛵"},
    {"id": "D3", "name": "Ravi Kumar",     "zone": "South",   "available": False, "current_orders": 2, "distance_from_hub_km": 4.1, "rating": 4.3, "completed_today": 7,  "emoji": "🏍️"},
    {"id": "D4", "name": "Meena Patel",    "zone": "East",    "available": True,  "current_orders": 0, "distance_from_hub_km": 3.0, "rating": 4.7, "completed_today": 11, "emoji": "🛵"},
    {"id": "D5", "name": "Vikram Nair",    "zone": "Central", "available": True,  "current_orders": 0, "distance_from_hub_km": 1.8, "rating": 4.9, "completed_today": 14, "emoji": "🏍️"},
    {"id": "D6", "name": "Sunita Rao",     "zone": "North",   "available": False, "current_orders": 1, "distance_from_hub_km": 2.2, "rating": 4.5, "completed_today": 8,  "emoji": "🛵"},
    {"id": "D7", "name": "Deepak Verma",   "zone": "West",    "available": True,  "current_orders": 0, "distance_from_hub_km": 3.5, "rating": 4.4, "completed_today": 6,  "emoji": "🏍️"},
]

# ── Pre-seeded Orders ─────────────────────────────────────────────────────────
def _ago(minutes):
    return (datetime.now() - timedelta(minutes=minutes)).isoformat()

SEED_ORDERS = [
    {
        "id": "ORD-101",
        "customer": "Rahul Mehta",
        "customer_phone": "+91-9876543210",
        "restaurant_id": "R1",
        "items": [{"menu_id": "M1", "name": "Butter Chicken", "qty": 2, "price": 299},
                  {"menu_id": "M4", "name": "Garlic Naan",   "qty": 4, "price": 49}],
        "total": 794,
        "status": "preparing",
        "delivery_zone": "North",
        "distance_km": 2.1,
        "placed_at": _ago(28),
        "assigned_partner": "D1",
        "priority_score": None,
        "notes": "Extra spicy",
    },
    {
        "id": "ORD-102",
        "customer": "Anita Desai",
        "customer_phone": "+91-9812345678",
        "restaurant_id": "R2",
        "items": [{"menu_id": "M5", "name": "Classic Smash Burger", "qty": 1, "price": 249},
                  {"menu_id": "M7", "name": "Loaded Fries",          "qty": 1, "price": 149}],
        "total": 398,
        "status": "out_for_delivery",
        "delivery_zone": "Central",
        "distance_km": 3.4,
        "placed_at": _ago(35),
        "assigned_partner": "D2",
        "priority_score": None,
        "notes": "",
    },
    {
        "id": "ORD-103",
        "customer": "Kiran Joshi",
        "customer_phone": "+91-9823456789",
        "restaurant_id": "R3",
        "items": [{"menu_id": "M9",  "name": "Dragon Roll",    "qty": 2, "price": 499},
                  {"menu_id": "M12", "name": "Edamame",        "qty": 1, "price": 99}],
        "total": 1097,
        "status": "pending",
        "delivery_zone": "South",
        "distance_km": 5.2,
        "placed_at": _ago(10),
        "assigned_partner": None,
        "priority_score": None,
        "notes": "Ring doorbell twice",
    },
    {
        "id": "ORD-104",
        "customer": "Priya Gupta",
        "customer_phone": "+91-9834567890",
        "restaurant_id": "R1",
        "items": [{"menu_id": "M3", "name": "Dal Makhani",  "qty": 1, "price": 199},
                  {"menu_id": "M2", "name": "Paneer Tikka", "qty": 2, "price": 249}],
        "total": 697,
        "status": "preparing",
        "delivery_zone": "North",
        "distance_km": 1.8,
        "placed_at": _ago(22),
        "assigned_partner": None,
        "priority_score": None,
        "notes": "",
    },
    {
        "id": "ORD-105",
        "customer": "Suresh Rao",
        "customer_phone": "+91-9845678901",
        "restaurant_id": "R2",
        "items": [{"menu_id": "M6", "name": "BBQ Chicken Burger", "qty": 2, "price": 279},
                  {"menu_id": "M8", "name": "Milkshake",           "qty": 2, "price": 119}],
        "total": 796,
        "status": "pending",
        "delivery_zone": "East",
        "distance_km": 4.5,
        "placed_at": _ago(8),
        "assigned_partner": None,
        "priority_score": None,
        "notes": "Chocolate milkshake please",
    },
    {
        "id": "ORD-106",
        "customer": "Meera Iyer",
        "customer_phone": "+91-9856789012",
        "restaurant_id": "R3",
        "items": [{"menu_id": "M10", "name": "Salmon Sashimi", "qty": 1, "price": 599},
                  {"menu_id": "M11", "name": "Miso Ramen",      "qty": 1, "price": 349}],
        "total": 948,
        "status": "out_for_delivery",
        "delivery_zone": "South",
        "distance_km": 3.8,
        "placed_at": _ago(45),
        "assigned_partner": "D3",
        "priority_score": None,
        "notes": "",
    },
    {
        "id": "ORD-107",
        "customer": "Ajay Patel",
        "customer_phone": "+91-9867890123",
        "restaurant_id": "R1",
        "items": [{"menu_id": "M1", "name": "Butter Chicken", "qty": 1, "price": 299}],
        "total": 299,
        "status": "preparing",
        "delivery_zone": "West",
        "distance_km": 6.1,
        "placed_at": _ago(18),
        "assigned_partner": None,
        "priority_score": None,
        "notes": "",
    },
    {
        "id": "ORD-108",
        "customer": "Divya Nair",
        "customer_phone": "+91-9878901234",
        "restaurant_id": "R3",
        "items": [{"menu_id": "M9", "name": "Dragon Roll", "qty": 1, "price": 499},
                  {"menu_id": "M10", "name": "Salmon Sashimi", "qty": 1, "price": 599}],
        "total": 1098,
        "status": "pending",
        "delivery_zone": "South",
        "distance_km": 5.8,
        "placed_at": _ago(15),
        "assigned_partner": None,
        "priority_score": None,
        "notes": "Gluten free soy sauce",
    },
    {
        "id": "ORD-109",
        "customer": "Ramesh Shah",
        "customer_phone": "+91-9889012345",
        "restaurant_id": "R2",
        "items": [{"menu_id": "M5", "name": "Classic Smash Burger", "qty": 3, "price": 249},
                  {"menu_id": "M7", "name": "Loaded Fries",          "qty": 2, "price": 149}],
        "total": 1045,
        "status": "preparing",
        "delivery_zone": "Central",
        "distance_km": 2.9,
        "placed_at": _ago(20),
        "assigned_partner": "D5",
        "priority_score": None,
        "notes": "Office delivery",
    },
    {
        "id": "ORD-110",
        "customer": "Sita Krishnan",
        "customer_phone": "+91-9890123456",
        "restaurant_id": "R1",
        "items": [{"menu_id": "M2", "name": "Paneer Tikka", "qty": 1, "price": 249},
                  {"menu_id": "M4", "name": "Garlic Naan",  "qty": 2, "price": 49}],
        "total": 347,
        "status": "delivered",
        "delivery_zone": "North",
        "distance_km": 2.3,
        "placed_at": _ago(60),
        "assigned_partner": "D6",
        "priority_score": None,
        "notes": "",
    },
    {
        "id": "ORD-111",
        "customer": "Vikash Agarwal",
        "customer_phone": "+91-9801234567",
        "restaurant_id": "R2",
        "items": [{"menu_id": "M6", "name": "BBQ Chicken Burger", "qty": 1, "price": 279}],
        "total": 279,
        "status": "delivered",
        "delivery_zone": "West",
        "distance_km": 3.7,
        "placed_at": _ago(75),
        "assigned_partner": "D7",
        "priority_score": None,
        "notes": "",
    },
    {
        "id": "ORD-112",
        "customer": "Lakshmi Venkat",
        "customer_phone": "+91-9812340987",
        "restaurant_id": "R3",
        "items": [{"menu_id": "M11", "name": "Miso Ramen", "qty": 2, "price": 349}],
        "total": 698,
        "status": "pending",
        "delivery_zone": "East",
        "distance_km": 7.2,
        "placed_at": _ago(5),
        "assigned_partner": None,
        "priority_score": None,
        "notes": "Extra egg",
    },
]

def get_prep_time_for_order(order, menu_items_dict):
    """Calculate total prep time for an order based on its items."""
    max_prep = 0
    for item in order.get("items", []):
        if not isinstance(item, dict):
            continue
        menu_id = item.get("menu_id") or item.get("id")
        menu = menu_items_dict.get(menu_id) if menu_id else None
        if menu and isinstance(menu, dict):
            max_prep = max(max_prep, menu.get("prep_time", 15))
    return max_prep + 5  # +5 for packaging


MENU_DICT = {m["id"]: m for m in MENU_ITEMS}
