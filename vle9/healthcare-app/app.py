import os
import re
import secrets
import hmac

from flask import (
    Flask, request, redirect, url_for,
    render_template_string, jsonify, session, g
)

app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.environ.get(
        "APP_SECRET_KEY",
        "local-demo-only-change-before-deployment"
    ),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
)

patients = [
    {"id": 1, "name": "Alex Morgan", "age": 32, "condition": "General Checkup"},
    {"id": 2, "name": "Sam Taylor", "age": 45, "condition": "Routine Follow-up"},
]

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MediSecure | Healthcare Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style nonce="{{ csp_nonce }}">
        body {
            font-family: Arial, sans-serif;
            background: #eef4fa;
            margin: 0;
            padding: 30px;
            color: #243447;
        }
        .container {
            max-width: 850px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 18px #0001;
        }
        h1 { color: #176b87; }
        .notice {
            background: #e2f5ef;
            padding: 12px;
            border-radius: 8px;
        }
        input {
            padding: 11px;
            margin: 7px 0;
            width: 95%;
            border: 1px solid #ccd6df;
            border-radius: 7px;
        }
        button {
            background: #176b87;
            color: white;
            padding: 12px 20px;
            border: 0;
            border-radius: 7px;
            cursor: pointer;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }
        th { background: #e2f0f5; }
        .error { color: #b42318; }
    </style>
</head>

<body>
<div class="container">

    <h1>MediSecure Healthcare Portal</h1>
    <p>Secure Patient Management Demonstration</p>

    <div class="notice">
        Security demonstration using fictional patient records only.
        No real medical information is stored.
    </div>

    <h2>Register a Patient</h2>

    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}

    <form method="POST" action="/patients">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">

        <input name="name" placeholder="Patient name"
               maxlength="60" required>

        <input name="age" type="number" placeholder="Age"
               min="1" max="120" required>

        <input name="condition" placeholder="Visit category"
               maxlength="60" required>

        <button type="submit">Register Patient</button>
    </form>

    <h2>Patient Records</h2>

    <table>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Age</th>
            <th>Visit Category</th>
        </tr>

        {% for patient in patients %}
        <tr>
            <td>{{ patient.id }}</td>
            <td>{{ patient.name }}</td>
            <td>{{ patient.age }}</td>
            <td>{{ patient.condition }}</td>
        </tr>
        {% endfor %}
    </table>

    <p><small>System status: Operational</small></p>

</div>
</body>
</html>
"""


@app.before_request
def prepare_security_tokens():
    g.csp_nonce = secrets.token_urlsafe(16)

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    # Prevent caching of patient information.
    response.headers["Cache-Control"] = "no-store"

    # CSP allows only this response's inline style block.
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"style-src 'self' 'nonce-{g.csp_nonce}'; "
        f"form-action 'self'; "
        f"frame-ancestors 'none'; "
        f"base-uri 'self'; "
        f"object-src 'none'"
    )

    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    return response


def render_home(error=None, status=200):
    return render_template_string(
        HTML,
        patients=patients,
        error=error,
        csrf_token=session["csrf_token"],
        csp_nonce=g.csp_nonce
    ), status


@app.route("/", methods=["GET"])
def home():
    return render_home()


@app.route("/patients", methods=["POST"])
def register_patient():

    submitted_token = request.form.get("csrf_token", "")
    expected_token = session.get("csrf_token", "")

    if not expected_token or not hmac.compare_digest(
        submitted_token, expected_token
    ):
        return "Invalid or missing CSRF token.", 400

    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    condition = request.form.get("condition", "").strip()

    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,59}", name):
        return render_home("Invalid patient name.", 400)

    if not age.isdigit() or not 1 <= int(age) <= 120:
        return render_home("Age must be between 1 and 120.", 400)

    if not re.fullmatch(r"[A-Za-z0-9 .'-]{1,60}", condition):
        return render_home("Invalid visit category.", 400)

    patients.append({
        "id": max(p["id"] for p in patients) + 1,
        "name": name,
        "age": int(age),
        "condition": condition
    })

    return redirect(url_for("home"))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "application": "MediSecure"
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
