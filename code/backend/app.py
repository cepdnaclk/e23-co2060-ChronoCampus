from flask import Flask
import psycopg2
from flask import jsonify
from flask import request

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="chronocampus",
        user="postgres",
        password="kali"
    )
    return conn

@app.route("/")
def home():
    return "ChronoCampus Backend Running"

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM rooms;")
        rooms = cur.fetchall()
        cur.close()
        conn.close()
        return str(rooms)
    except Exception as e:
        return str(e)
    


@app.route("/rooms", methods=["GET"])
def get_rooms():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms;")
    rooms = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rooms)


@app.route("/reserve", methods=["POST"])
def reserve_room():
    data = request.get_json()

    user_id = data["user_id"]
    room_id = data["room_id"]
    date = data["date"]
    start_time = data["start_time"]
    end_time = data["end_time"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Check overlap
    cur.execute("""
        SELECT * FROM reservations
        WHERE room_id = %s
        AND date = %s
        AND (
            (start_time < %s AND end_time > %s)
        )
    """, (room_id, date, end_time, start_time))

    conflict = cur.fetchone()

    if conflict:
        cur.close()
        conn.close()
        return jsonify({"error": "Time slot already booked"}), 400


    # Insert if no conflict
    cur.execute("""
        INSERT INTO reservations (user_id, room_id, date, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, room_id, date, start_time, end_time))

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Reservation created successfully"}

@app.route("/reservations", methods=["GET"])
def get_reservations_by_date():
    date = request.args.get("date")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT r.id, u.username, rm.room_name, r.date, r.start_time, r.end_time
        FROM reservations r
        JOIN users u ON r.user_id = u.id
        JOIN rooms rm ON r.room_id = rm.id
        WHERE r.date = %s
        ORDER BY r.start_time
    """, (date,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "reservation_id": row[0],
            "username": row[1],
            "room": row[2],
            "date": str(row[3]),
            "start_time": str(row[4]),
            "end_time": str(row[5])
        })

    return jsonify(result)



if __name__ == "__main__":
    app.run(debug=True)
