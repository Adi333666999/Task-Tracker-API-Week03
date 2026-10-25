from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory database to store tasks
tasks = []
current_id = 1


# 1. GET /health - Checks if the API is running
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


# 2. POST /tasks - Creates a new task
@app.route("/tasks", methods=["POST"])
def create_task():
    global current_id
    data = request.get_json()

    # Validation: Ensure 'title' is provided in the request body
    if not data or "title" not in data:
        return jsonify({"error": "Title is required"}), 400

    new_task = {
        "id": current_id,
        "title": data["title"],
        "description": data.get("description", ""),  # Optional field
        "completed": data.get("completed", False),  # Defaults to False
    }

    tasks.append(new_task)
    current_id += 1

    return jsonify(new_task), 201


# 3. GET /tasks - Retrieves all tasks
@app.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks), 200


if __name__ == "__main__":
    app.run(debug=True)
