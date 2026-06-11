from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from dotenv import load_dotenv
import os
app = Flask(__name__)
CORS(app)



load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

@app.route('/api/users', methods=['GET'])
def get_users():
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM users")

    rows = cursor.fetchall()

    users = [
        {
            "id": row[0],
            "name": row[1]
        }
        for row in rows
    ]

    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()

    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (name) VALUES (%s) RETURNING id",
        (data["name"],)
    )

    user_id = cursor.fetchone()[0]

    conn.commit()

    return jsonify({
        "id": user_id,
        "name": data["name"]
    }), 201

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.get_json()

    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET name = %s WHERE id = %s",
        (data["name"], id)
    )

    if cursor.rowcount == 0:
        return jsonify({"message": "User not found"}), 404

    conn.commit()

    return jsonify({
        "message": "User updated successfully"
    }), 200

@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM users WHERE id = %s",
        (id,)
    )

    if cursor.rowcount == 0:
        return jsonify({"message": "User not found"}), 404

    conn.commit()

    return jsonify({
        "message": "User deleted successfully"
    }), 200

if __name__ == '__main__':
    app.run(debug=True)