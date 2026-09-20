"""
Al-Harmain Rice — Order API
----------------------------
Website orders yahan aa kar store hote hain (SQLite file mein).
Aapka local Python software is API se GET /orders call kar ke
naye orders utha sakta hai, aur unhein "fetched" mark kar sakta hai.

Deploy: Render.com, PythonAnywhere, Railway, ya koi bhi Python hosting.
"""

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")

# Is key ko change kar dein — website aur aapke Python software
# dono mein wahi key honi chahiye (simple security ke liye)
API_KEY = os.environ.get("ALHARMAIN_API_KEY", "change-this-secret-key")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


DEFAULT_CONFIG = {
    "bank_name": "[Aapka Bank]",
    "account_title": "Al-Harmain Rice Traders",
    "account_number": "XXXX-XXXXXXXX-XX",
    "iban": "PKXX XXXX XXXX XXXX XXXX XXXX",
    "phone": "+92 300 0000000",
    "whatsapp": "923000000000",
    "email": "info@alharmainrice.pk",
    "address": "Jalalpur Bhattian Road, Hafizabad, Punjab, Pakistan",
    "products": [],
}


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            address TEXT,
            payment_method TEXT,
            items_json TEXT,
            total REAL,
            created_at TEXT,
            fetched INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            config_json TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def check_key():
    key = request.headers.get("X-API-Key")
    return key == API_KEY


@app.route("/api/orders", methods=["POST"])
def create_order():
    """Website is endpoint par naya order bhejti hai."""
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True, silent=True) or {}
    required = ["customer_name", "phone", "items", "total"]
    if not all(k in data for k in required):
        return jsonify({"error": "missing fields", "required": required}), 400

    conn = get_db()
    conn.execute(
        """INSERT INTO orders
           (customer_name, phone, address, payment_method, items_json, total, created_at, fetched)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (
            data["customer_name"],
            data["phone"],
            data.get("address", ""),
            data.get("payment_method", ""),
            json.dumps(data["items"]),
            float(data["total"]),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    order_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return jsonify({"status": "ok", "order_id": order_id}), 201


@app.route("/api/orders", methods=["GET"])
def list_orders():
    """
    Aapka Python software yahan se orders utha ta hai.
    ?only_new=true dein to sirf abhi tak na-uthaye gaye orders milenge.
    """
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    only_new = request.args.get("only_new", "false").lower() == "true"
    conn = get_db()
    if only_new:
        rows = conn.execute("SELECT * FROM orders WHERE fetched = 0 ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM orders ORDER BY id").fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "customer_name": r["customer_name"],
            "phone": r["phone"],
            "address": r["address"],
            "payment_method": r["payment_method"],
            "items": json.loads(r["items_json"]),
            "total": r["total"],
            "created_at": r["created_at"],
            "fetched": bool(r["fetched"]),
        })
    return jsonify(result)


@app.route("/api/orders/<int:order_id>/mark_fetched", methods=["POST"])
def mark_fetched(order_id):
    """Python software order utha kar isay 'fetched' mark kar de."""
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db()
    conn.execute("UPDATE orders SET fetched = 1 WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/config", methods=["GET"])
def get_config():
    """Website is se apna poora content (products, bank, contact) load karti hai.
    Public hai (login/key ki zaroorat nahi) taake har visitor ki website khul sake."""
    conn = get_db()
    row = conn.execute("SELECT config_json FROM site_config WHERE id = 1").fetchone()
    conn.close()
    if row:
        return jsonify(json.loads(row["config_json"]))
    return jsonify(DEFAULT_CONFIG)


@app.route("/api/config", methods=["POST"])
def save_config():
    """Sirf aapka software (Website Settings screen) is se naya content bhejta hai."""
    if not check_key():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True, silent=True) or {}
    conn = get_db()
    conn.execute("""
        INSERT INTO site_config (id, config_json, updated_at) VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET config_json=excluded.config_json, updated_at=excluded.updated_at
    """, (json.dumps(data), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Al-Harmain order API chal raha hai"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
