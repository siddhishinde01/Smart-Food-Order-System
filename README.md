# FoodTech — Smart Food Delivery Order Management Platform

> **Hackathon MVP** — AI-powered intelligent order management system

---

## Quick Start

```bash
cd foodtech
pip install flask flask-cors
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## Demo Flow (Hackathon Presentation)

| Step | What to show | URL |
|------|-------------|-----|
| 1 | Customer orders food | `/` → pick restaurant → add to cart → checkout |
| 2 | Order appears in Command Center | `/dashboard` |
| 3 | AI Priority Engine scores | Dashboard → Live Order Queue |
| 4 | Click any order → see score + reasoning | Modal |
| 5 | Delay Monitor | Dashboard → Delay Monitor tab |
| 6 | What-If Simulator | Dashboard → What-If Simulator tab |
| 7 | AI Recommendations | Dashboard → AI Recommendations tab |

---

## Architecture

```
foodtech/
├── app.py                    # Flask app + all routes
├── data/
│   └── sample_data.py        # 12 seeded orders, 3 restaurants, 7 partners, 12 menu items
├── services/
│   ├── priority_engine.py    # AI Priority Score (0-100) with 6 weighted factors
│   ├── delay_predictor.py    # Predictive Delay Monitor
│   ├── assignment_engine.py  # Smart delivery partner assignment + batching
│   └── recommendation_engine.py  # AI recommendations + What-If simulation
├── templates/                # Jinja2 HTML templates
│   ├── index.html            # Homepage with live stats
│   ├── menu.html             # Restaurant menu + cart drawer
│   ├── cart.html             # Cart review page
│   ├── checkout.html         # Checkout form
│   ├── order_confirmation.html
│   ├── tracking.html         # Live order tracking
│   └── dashboard.html        # Command Center (main demo screen)
└── static/
    ├── css/style.css         # Global design system (purple/white)
    ├── css/dashboard.css     # Dashboard-specific styles
    └── js/
        ├── app.js            # Shared utilities (cart, toasts)
        └── dashboard.js      # Full dashboard logic
```

---

## AI Intelligence Engine

### Priority Score Formula

```
score = (
  waiting_time    × 0.25  +
  prep_time       × 0.20  +
  distance        × 0.15  +
  restaurant_load × 0.20  +
  partner_scarcity× 0.10  +
  eta_risk        × 0.10
) × 100
```

**Classifications:**
- `CRITICAL` — score ≥ 80
- `HIGH`     — score ≥ 60
- `NORMAL`   — score ≥ 35
- `LOW`      — score < 35

Each factor is normalized 0–1 and explained in plain English per order.

### Delay Prediction

Estimates `estimated_total_time = waiting + remaining_prep + travel + kitchen_overhead`
and computes delay = `estimated_total - 45 min promise`.

### Delivery Assignment

Scores every available partner on:
- Availability + current load
- Distance from restaurant hub
- Zone match with delivery destination
- Customer rating

---

## Key Features

- [x] Customer ordering (Home → Menu → Cart → Checkout → Confirmation → Tracking)
- [x] AI Priority Score engine (real formula, 6 factors, human-readable reasoning)
- [x] Command Center dashboard with 6 KPI cards
- [x] Live Order Queue with sortable table + priority indicators
- [x] AI Recommendations panel (auto-generated from live data)
- [x] Predictive Delay Monitor (per-order risk + predicted delay minutes)
- [x] What-If Simulator (surge simulation with before/after comparison)
- [x] Smart Delivery Partner Assignment (recommended + rationale)
- [x] Smart Order Batching (zone-based nearby delivery detection)
- [x] 4 Analytics charts (Chart.js)
- [x] Auto-refresh every 30s
- [x] Order status update from dashboard
- [x] Order detail modal with full breakdown

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x + Flask |
| Frontend | HTML5 + Vanilla CSS + JavaScript (ES6+) |
| Charts | Chart.js 4.x (CDN) |
| Fonts | Inter (Google Fonts) |
| Data | In-memory Python structures |
| AI | Local scoring/recommendation engine (no external API required) |

---

## No Authentication Required

The app is open — no login needed. Perfect for hackathon demo.
