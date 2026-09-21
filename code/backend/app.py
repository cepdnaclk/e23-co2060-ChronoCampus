
# Setup & Database Connection (Creates Flask app, Connects to PostgreSQL database)
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, time
import psycopg2, os
from dotenv import load_dotenv

from config import Config
from database import db
from models.room import Room
from models.reservation import Reservation
from models.override_request import OverrideRequest
from models.notification import Notification
from models.watchlist import RoomWatchlist
from models.waitlist import RoomWaitlistQueue as RoomWaitlist
from models.users import User
from routes.reservation_routes import reservation_bp
from routes.watchlist_routes import watchlist_bp
from routes.auth_routes import auth_bp

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, '..', 'frontend'),
    static_folder=os.path.join(BASE_DIR, '..', 'frontend')
)

app.secret_key = os.getenv("SECRET_KEY")

app.config.from_object(Config)
CORS(app, supports_credentials=True)


db.init_app(app)


with app.app_context():
    db.create_all()
    print(" Tables ready!")
    print(" DB URI:", app.config["SQLALCHEMY_DATABASE_URI"])


app.register_blueprint(reservation_bp)
app.register_blueprint(watchlist_bp)
app.register_blueprint(auth_bp)

# =========================
# DATABASE CONNECTION
# =========================
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# Home Page
@app.route("/")
def home():
    return render_template("index.html")

# =========================
# API 01 - CURRENT STATUS
# =========================

@app.route("/rooms/current-status", methods=["GET"])
def current_status():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT room_id, room_name FROM rooms")
    rooms = cur.fetchall()

    result = []

    for room in rooms:
        room_id, room_name = room

        cur.execute("""
            SELECT start_time, end_time
            FROM reservations
            WHERE room_id = %s
            AND reservation_date = CURRENT_DATE
            AND CURRENT_TIMESTAMP BETWEEN start_time AND end_time
        """, (room_id,))

        booking = cur.fetchone()

        if booking:
            result.append({
                "room_id": room_id,
                "room_name": room_name,
                "status": "Occupied",
                "booked_from": str(booking[0]),
                "booked_to": str(booking[1])
            })
        else:
            result.append({
                "room_id": room_id,
                "room_name": room_name,
                "status": "Free"
            })

    cur.close()
    conn.close()

    return jsonify(result)


# =========================
# API 02 - DAILY SCHEDULE
# =========================
@app.route("/rooms/schedule", methods=["GET"])
def daily_schedule():
    date = request.args.get("date")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT room_id, room_name FROM rooms")
    rooms = cur.fetchall()

    output = []

    for room in rooms:
        room_id, room_name = room

        cur.execute("""
            SELECT start_time, end_time
            FROM reservations
            WHERE room_id = %s
            AND reservation_date = %s
            ORDER BY start_time
        """, (room_id, date))

        bookings = cur.fetchall()

        booking_list = []
        for b in bookings:
            booking_list.append({
                "start": str(b[0]),
                "end": str(b[1])
            })

        output.append({
            "room_id": room_id,
            "room_name": room_name,
            "bookings": booking_list
        })

    cur.close()
    conn.close()

    return jsonify(output)


# =========================
# API 03 - SEARCH ROOM
# =========================
@app.route("/rooms/search", methods=["GET"])
def search_room():
    name = request.args.get("name")
    date = request.args.get("date")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT room_id, room_name
        FROM rooms
        WHERE room_name ILIKE %s
    """, (f"%{name}%",))

    rooms = cur.fetchall()

    result = []

    for room in rooms:
        room_id, room_name = room

        cur.execute("""
            SELECT start_time, end_time
            FROM reservations
            WHERE room_id = %s
            AND reservation_date = %s
            ORDER BY start_time
        """, (room_id, date))

        bookings = cur.fetchall()

        booking_list = []
        for b in bookings:
            booking_list.append({
                "start": str(b[0]),
                "end": str(b[1])
            })

        result.append({
            "room_id": room_id,
            "room_name": room_name,
            "bookings": booking_list
        })

    cur.close()
    conn.close()

    return jsonify(result)


#Loads DIRECTORY PAGE UI
@app.route("/directory")
def directory():
    return render_template("directory.html")


# GET ALL USERS (API)
@app.route("/api/users")
def get_users():


    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
    SELECT 
        u.user_id,
        u.full_name AS username,
        u.role,
        COALESCE(f.department, '') AS department,
        COALESCE(f.office_location, '') AS location,
        COALESCE(f.profile_image, NULL) AS image,
        u.email
    FROM users u
    LEFT JOIN find_users f ON u.user_id = f.user_id

    UNION ALL

    SELECT 
        f.user_id,
        f.username,
        f.role,
        f.department,
        f.office_location,
        f.profile_image,
        NULL AS email
    FROM find_users f
    WHERE NOT EXISTS (
        SELECT 1 FROM users u WHERE u.user_id = f.user_id
    );
    """)


    rows = cur.fetchall()


    users = []
    for r in rows:
        users.append({
            "id": r[0],
            "name": r[1],
            "role": r[2],
            "department": r[3],
            "location": r[4],
            "image": r[5],
            "email": r[6]
        })


    cur.close()
    conn.close()


    return jsonify(users)


# =========================
# API 04 - ROOM AVAILABILITY
# =========================

@app.route("/rooms/availability", methods=["GET"])
def room_availability():
    room_id = request.args.get("room_id")
    date = request.args.get("date")

    working_start = datetime.strptime(date + " 08:00:00", "%Y-%m-%d %H:%M:%S")
    working_end = datetime.strptime(date + " 17:00:00", "%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT start_time, end_time
        FROM reservations
        WHERE room_id = %s
        AND reservation_date = %s
        ORDER BY start_time
    """, (room_id, date))

    bookings = cur.fetchall()

    free_slots = []
    current_pointer = working_start

    for booking in bookings:
        start, end = booking

        if start > current_pointer:
            free_slots.append({
                "start": str(current_pointer),
                "end": str(start)
            })

        current_pointer = max(current_pointer, end)

    if current_pointer < working_end:
        free_slots.append({
            "start": str(current_pointer),
            "end": str(working_end)
        })

    cur.close()
    conn.close()

    return jsonify({
        "room_id": room_id,
        "free_slots": free_slots
    })


# ADMIN PAGE
@app.route("/admin")
def admin_page():
    return render_template("admin.html")

# MAIN API (Manage Users)
@app.route("/api/manage_user", methods=["POST"])
def manage_user():

    username = request.form.get("username")
    email = request.form.get("email")
    role = request.form.get("role")
    department = request.form.get("department")
    location = request.form.get("location")
    action = request.form.get("action")

    image_file = request.files.get("image")
    image_path = None

    if image_file:
        filename = image_file.filename
        image_folder = os.path.join(BASE_DIR, '..', 'images')
        save_path = os.path.join(image_folder, filename)

        image_file.save(save_path)

        image_path = filename   # store ONLY filename

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        # -------- ADD (ADMIN ONLY → find_users) --------
        if action == "add":

            # generate new user_id manually
            cur.execute("SELECT COALESCE(MAX(user_id),0)+1 FROM find_users")
            user_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO find_users
                (user_id, username, role, department, office_location, profile_image)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (user_id, username, role, department, location, image_path))

            conn.commit()
            return jsonify({"message": "User added (admin)"})

        # -------- UPDATE (LOGIN USERS → create profile if needed) --------
        elif action == "update":

            # get user_id from users table
            cur.execute("""
                SELECT user_id FROM users WHERE full_name=%s
            """, (username,))
            user = cur.fetchone()

            if not user:
                cur.execute("SELECT user_id FROM find_users WHERE username=%s", (username,))
                user = cur.fetchone()

            user_id = user[0]

            # check if profile exists
            cur.execute("""
                SELECT user_id FROM find_users WHERE user_id=%s
            """, (user_id,))
            exists = cur.fetchone()

            if exists:
                # UPDATE
                if image_path:
                    cur.execute("""
                    UPDATE find_users
                    SET department=%s,
                        office_location=%s,
                        profile_image=%s
                    WHERE user_id=%s
                    """,(department, location, image_path, user_id))
                else:
                    cur.execute("""
                    UPDATE find_users
                    SET department=%s,
                        office_location=%s
                    WHERE user_id=%s
                    """,(department, location, user_id))
            else:
                # INSERT (first time profile creation)
                cur.execute("""
                    INSERT INTO find_users
                    (user_id, username, role, department, office_location, profile_image)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (user_id, username, role, department, location, image_path))

            conn.commit()
            return jsonify({"message": "Profile updated"})

        # -------- DELETE --------
        elif action == "delete":

            cur.execute("""
                DELETE FROM find_users WHERE username=%s
            """, (username,))

            conn.commit()
            return jsonify({"message": "Deleted"})

        return jsonify({"message": "Invalid action"}), 400

    except Exception as e:
        conn.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cur.close()
        conn.close()

# ---------------- STAFF PROFILE ----------------


@app.route("/staff/<int:staff_id>")
def staff_profile(staff_id):
    return render_template("staff_profile.html", staff_id=staff_id)

@app.route("/api/staff/<int:staff_id>")
def get_staff(staff_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT username, department, office_location, profile_image
        FROM find_users
        WHERE user_id = %s
    """, (staff_id,))

    r = cur.fetchone()

    cur.close()
    conn.close()

    if not r:
        return jsonify({"error": "Profile not found"}), 404

    return jsonify({
        "name": r[0],
        "department": r[1],
        "location": r[2],
        "image": r[3]
    })


# ---------------- PAGES ----------------
@app.route("/edit/<int:user_id>")
def edit_page(user_id):
    return render_template("edit_user.html", user_id=user_id)

@app.route("/add")
def add_page():
    return render_template("add_user.html")

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, '..', 'images'),
        filename
    )

@app.route("/home4")
def home4():
    return render_template("home.html")


@app.route("/room")
def room_page():
    return render_template("index2.html")

@app.route("/current")
def current_page():
    return render_template("current.html")

@app.route("/schedule")
def schedule_page():
    return render_template("schedule.html")

@app.route("/search")
def search_page():
    return render_template("search.html")

@app.route("/availability")
def availability_page():
    return render_template("availability.html")


# LOGIN PAGE
@app.route("/login")
def login_page():
    return render_template("login.html")

# SIGNUP PAGE
@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard1():
    return render_template("dashboard.html")

@app.route("/booking")
def booking1():
    return render_template("booking.html")

@app.route("/my_reservations")
def my_reservation1():
    return render_template("my_reservations.html")

@app.route("/admin")
def admin1():
    return render_template("admin.html")

@app.route("/admin4")
def admin4():
    return render_template("admin4.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)

