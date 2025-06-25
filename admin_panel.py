from flask import Flask, render_template, request, redirect, session, jsonify
import json
import uuid
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "admin_secret_786"

LICENSE_FILE = "licenses.json"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ---------- Helper: load / save ----------
def load_licenses():
    if not os.path.exists(LICENSE_FILE):
        return []
    with open(LICENSE_FILE, "r") as f:
        return json.load(f)


def save_licenses(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------- Auth ----------
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form["username"] == ADMIN_USERNAME
            and request.form["password"] == ADMIN_PASSWORD
        ):
            session["admin"] = True
            return redirect("/admin/dashboard")
        return "Invalid credentials"
    return render_template("login.html")


# ---------- Dashboard ----------
@app.route("/admin/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/admin/login")
    licenses = load_licenses()
    return render_template("dashboard.html", licenses=licenses)


# ---------- Generate ----------
@app.route("/admin/generate", methods=["GET", "POST"])
def generate():
    if "admin" not in session:
        return redirect("/admin/login")

    if request.method == "POST":
        school = request.form.get("school_name")
        validity_days = int(request.form.get("validity_days", 365))

        licenses = load_licenses()
        new_license = {
            "key": f"{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}",
            "school": school,
            "activated_on": None,
            "expires_on": (datetime.now() + timedelta(days=validity_days)).strftime(
                "%Y-%m-%d"
            ),
            "activated_ip": None,
            "status": "active",
        }
        licenses.append(new_license)
        save_licenses(licenses)
        return redirect("/admin/dashboard")

    return render_template("generate.html")


# ---------- Enable / Disable ----------
@app.route("/admin/disable/<key>")
def disable(key):
    licenses = load_licenses()
    for lic in licenses:
        if lic["key"] == key:
            lic["status"] = "disabled"
            break
    save_licenses(licenses)
    return redirect("/admin/dashboard")


@app.route("/admin/enable/<key>")
def enable(key):
    licenses = load_licenses()
    for lic in licenses:
        if lic["key"] == key:
            lic["status"] = "active"
            break
    save_licenses(licenses)
    return redirect("/admin/dashboard")


# ---------- API for school app ----------
@app.route("/api/check-license")
def api_check():
    key = request.args.get("key")
    ip = request.args.get("ip")

    licenses = load_licenses()
    for lic in licenses:
        if lic["key"] == key:
            if lic["status"] != "active":
                return jsonify({"status": "disabled"})
            if lic["activated_ip"] and lic["activated_ip"] != ip:
                return jsonify({"status": "ip_mismatch"})
            if not lic["activated_ip"]:
                lic["activated_ip"] = ip
                lic["activated_on"] = datetime.now().strftime("%Y-%m-%d")
                save_licenses(licenses)
            if datetime.now() > datetime.strptime(lic["expires_on"], "%Y-%m-%d"):
                return jsonify({"status": "expired"})
            return jsonify(
                {
                    "status": "valid",
                    "school": lic["school"],
                    "expires_on": lic["expires_on"],
                }
            )

    return jsonify({"status": "invalid"})


# ---------- Run (dynamic port for Render) ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))  # Render sets PORT env; local default 5050
    app.run(host="0.0.0.0", port=port, debug=True)
