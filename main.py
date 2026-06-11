from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

users = [
    {"id": 1, "name": "John"},
    {"id": 2, "name": "Jane"}
]

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()

    new_user = {
        "id": len(users) + 1,
        "name": data["name"]
    }

    users.append(new_user)

    return jsonify({
        "message": "User created successfully",
        "user": new_user
    }), 201
@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.get_json()

    for user in users:
        if user["id"] == id:
            user["name"] = data.get("name")

            return jsonify({
                "message": "User updated successfully",
                "user": user
            }), 200

    return jsonify({"message": "User not found"}), 404
@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    global users

    for user in users:
        if user["id"] == id:
            users.remove(user)

            return jsonify({
                "message": "User deleted successfully"
            }), 200

    return jsonify({
        "message": "User not found"
    }), 404
if __name__ == '__main__':
    app.run(debug=True)