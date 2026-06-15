from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
import psycopg2
from dotenv import load_dotenv
import os
import jwt
import datetime
import bcrypt

app = Flask(__name__)
CORS(app)
load_dotenv()

app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
app.config["JWT_EXPIRY_HOURS"] = int(os.getenv("JWT_EXPIRY_HOURS", 24))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

# ─── JWT Helper ───────────────────────────────────────────────────────────────

def generate_token(user_id, email):
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=app.config["JWT_EXPIRY_HOURS"]),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")


def jwt_required(f):
    """Decorator to protect routes — expects Authorization: Bearer <token>"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"message": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])
            request.current_user = payload          # available inside the route
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    """
    Body: { "email": "...", "password": "...", "name": "..." }
    Creates a new user with a hashed password and returns a JWT.
    """
    data = request.get_json()
    email    = (data or {}).get("email", "").strip().lower()
    password = (data or {}).get("password", "")
    name     = (data or {}).get("name", "").strip()

    if not email or not password or not name:
        return jsonify({"message": "email, password and name are required"}), 400

    cursor = conn.cursor()

    # Check duplicate
    cursor.execute("SELECT id FROM active_users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"message": "Email already registered"}), 409

    # Hash password
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cursor.execute(
        "INSERT INTO active_users (email, password, name) VALUES (%s, %s, %s) RETURNING id",
        (email, hashed, name)
    )
    user_id = cursor.fetchone()[0]
    conn.commit()

    token = generate_token(user_id, email)
    return jsonify({
        "token": token,
        "user": {"id": user_id, "email": email, "name": name}
    }), 201


@app.route("/auth/login", methods=["POST"])
def login():
    """
    Body: { "email": "...", "password": "..." }
    Verifies credentials and returns a JWT.
    """
    data = request.get_json()
    email    = (data or {}).get("email", "").strip().lower()
    password = (data or {}).get("password", "")

    if not email or not password:
        return jsonify({"message": "email and password are required"}), 400

    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password, name FROM active_users WHERE email = %s", (email,))
    row = cursor.fetchone()

    if not row:
        return jsonify({"message": "Invalid email or password"}), 401

    user_id, db_email, db_hash, db_name = row

    if not bcrypt.checkpw(password.encode(), db_hash.encode()):
        return jsonify({"message": "Invalid email or password"}), 401

    token = generate_token(user_id, db_email)
    return jsonify({
        "token": token,
        "user": {"id": user_id, "email": db_email, "name": db_name}
    }), 200


@app.route("/auth/me", methods=["GET"])
@jwt_required
def me():
    """Returns the currently authenticated user (token introspection)."""
    user = request.current_user
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name FROM active_users WHERE id = %s", (user["user_id"],))
    row = cursor.fetchone()
    if not row:
        return jsonify({"message": "User not found"}), 404
    return jsonify({"id": row[0], "email": row[1], "name": row[2]}), 200


# ─── Protected User Routes ────────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@jwt_required
def get_users():
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users")
    rows = cursor.fetchall()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])


@app.route("/api/users", methods=["POST"])
@jwt_required
def create_user():
    data = request.get_json()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name) VALUES (%s) RETURNING id", (data["name"],))
    user_id = cursor.fetchone()[0]
    conn.commit()
    return jsonify({"id": user_id, "name": data["name"]}), 201


@app.route("/api/users/<int:id>", methods=["PUT"])
@jwt_required
def update_user(id):
    data = request.get_json()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = %s WHERE id = %s", (data["name"], id))
    if cursor.rowcount == 0:
        return jsonify({"message": "User not found"}), 404
    conn.commit()
    return jsonify({"message": "User updated successfully"}), 200


@app.route("/api/users/<int:id>", methods=["DELETE"])
@jwt_required
def delete_user(id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (id,))
    if cursor.rowcount == 0:
        return jsonify({"message": "User not found"}), 404
    conn.commit()
    return jsonify({"message": "User deleted successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True)