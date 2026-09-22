import re
import bcrypt
import psycopg2
from flask import Blueprint, request, jsonify
from config import Config

auth_bp = Blueprint("auth", __name__)

ALLOWED_DEPARTMENTS = [
    "Computer Engineering",
    "Electrical And Electronic Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Chemical Engineering",
    "Manufacturing And Industrial Engineering",
    "Mathematics"
]

# ── DB connection via psycopg2 (member 1's approach) ──────────────────────────
def get_db():
    return psycopg2.connect(**Config.PSYCOPG2_CONN)

# ── Password strength ──────────────────────────────────────────────────────────
def is_strong_password(password):
    if len(password) < 8:              return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[0-9]", password): return False
    return True

# ── Determine role from university email ───────────────────────────────────────

def get_role_from_email(email):
    admin_email     = "donotreply@pdn.ac.lk"
    student_domain  = "@eng.pdn.ac.lk"
    staff_domains   = ["@eng.pdn.ac.lk", "@ee.pdn.ac.lk"]
    username        = email.split("@")[0]

    if email == admin_email:
        return "admin"

    if email.endswith(student_domain) and re.match(r"^e\d{5}$", username):
        return "student"

    for domain in staff_domains:
        if email.endswith(domain) and re.match(r"^[a-zA-Z]+$", username):
            return "staff"

    return None

# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    full_name  = data.get("full_name",  "").strip()
    email      = data.get("email",      "").strip().lower()
    password   = data.get("password",   "")
    department = data.get("department", "").strip()

    if not full_name or not email or not password or not department:
        return jsonify({"error": "All fields are required"}), 400

    if department not in ALLOWED_DEPARTMENTS:
        return jsonify({"error": "Invalid department selected"}), 400

    if not is_strong_password(password):
        return jsonify({
            "error": "Password must be at least 8 characters and include uppercase, lowercase, and a number"
        }), 400

    role = get_role_from_email(email)
    if not role:
        #return jsonify({"error": "Only university emails (@eng.pdn.ac.lk) are allowed"}), 400
        return jsonify({"error": "Students must use e-number emails (@eng.pdn.ac.lk); staff may use @eng.pdn.ac.lk or @ee.pdn.ac.lk"}), 400

    # enforce @ee.pdn.ac.lk only for Electrical And Electronic Engineering staff 
    if email.endswith("@ee.pdn.ac.lk") and department != "Electrical And Electronic Engineering":
        return jsonify({
        "error": "@ee.pdn.ac.lk emails are only allowed for Electrical And Electronic Engineering department"}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (full_name, email, password_hash, role, department)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id;
        """, (full_name, email, hashed, role, department))
        user_id = cur.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        return jsonify({"error": "Email already registered"}), 400
    finally:
        cur.close()
        conn.close()

    return jsonify({
        "message": "Account created successfully! Please login.",
        "role":    role,
        "user_id": user_id
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    email    = data.get("email",    "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT user_id, full_name, email, password_hash, role, is_active
        FROM users WHERE email = %s;
    """, (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    user_id, full_name, user_email, password_hash, role, is_active = user

    # bcrypt check — with plain-text fallback for dev seed (admin / 123)
    try:
        password_ok = bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        password_ok = (password == password_hash)

    if not password_ok:
        return jsonify({"error": "Invalid email or password"}), 401

    if not is_active:
        return jsonify({"error": "Account is deactivated. Contact admin."}), 403

    return jsonify({
        "message": "Login successful",
        "user": {
            "user_id":   user_id,
            "full_name": full_name,
            "email":     user_email,
            "role":      role
        }
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"}), 200


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/auth/change-password", methods=["PUT"])
def change_password():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    email        = data.get("email",        "").strip().lower()
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not email or not old_password or not new_password:
        return jsonify({"error": "All fields are required"}), 400

    if not is_strong_password(new_password):
        return jsonify({
            "error": "New password must be at least 8 characters with uppercase, lowercase, and a number"
        }), 400

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT password_hash FROM users
        WHERE email = %s AND is_active = TRUE;
    """, (email,))
    row = cur.fetchone()

    if not row:
        cur.close(); conn.close()
        return jsonify({"error": "User not found or inactive"}), 404

    try:
        old_ok = bcrypt.checkpw(old_password.encode("utf-8"), row[0].encode("utf-8"))
    except Exception:
        old_ok = (old_password == row[0])

    if not old_ok:
        cur.close(); conn.close()
        return jsonify({"error": "Old password is incorrect"}), 401

    new_hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.execute("""
        UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
        WHERE email = %s;
    """, (new_hashed, email))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Password changed successfully"}), 200