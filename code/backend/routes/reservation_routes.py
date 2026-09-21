from flask import Blueprint, request, jsonify
from database import db
from models.reservation import Reservation
from models.room import Room
from models.users import User
from models.override_request import OverrideRequest
from models.notification import Notification
from models.watchlist import RoomWatchlist
from models.waitlist import RoomWaitlistQueue as RoomWaitlist
from datetime import datetime, timedelta

reservation_bp = Blueprint("reservations", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — notify watchers + advance waitlist queue when a slot opens
# ─────────────────────────────────────────────────────────────────────────────
def _notify_waitlist_and_watchers(reservation):
    room = reservation.room

    # Watchlist notifications
    watchers = RoomWatchlist.query.filter_by(
        room_id=reservation.room_id,
        reservation_date=reservation.reservation_date
    ).all()
    for w in watchers:
        db.session.add(Notification(
            user_id=w.user_id,
            message=(
                f"🟢 Room Available: {room.room_name} is now available on "
                f"{reservation.reservation_date} "
                f"({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}). "
                f"Book it now!"
            ),
            is_read=False
        ))

    # Waitlist queue — notify #1, shift everyone else up
    queue = RoomWaitlist.query.filter_by(
        room_id=reservation.room_id,
        reservation_date=reservation.reservation_date,
        status="waiting"
    ).filter(
        RoomWaitlist.start_time == reservation.start_time,
        RoomWaitlist.end_time   == reservation.end_time
    ).order_by(RoomWaitlist.queue_position).all()

    if queue:
        first = queue[0]
        first.status = "notified"
        db.session.add(Notification(
            user_id=first.user_id,
            message=(
                f"🎯 You're #1 in the queue! {room.room_name} on "
                f"{reservation.reservation_date} "
                f"({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}) "
                f"is now available. Book it before someone else does!"
            ),
            is_read=False
        ))
        for entry in queue[1:]:
            entry.queue_position -= 1
            db.session.add(Notification(
                user_id=entry.user_id,
                message=(
                    f"📋 Queue Update: You are now #{entry.queue_position} in line for "
                    f"{room.room_name} on {reservation.reservation_date} "
                    f"({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')})."
                ),
                is_read=False
            ))


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — Feature 3: Smart room suggestion
# ─────────────────────────────────────────────────────────────────────────────
def _suggest_alternative(room_id, start_time_dt, end_time_dt):
    original = Room.query.get(room_id)
    if not original:
        return None
    candidates = Room.query.filter(
        Room.room_id != room_id,
        Room.capacity >= original.capacity
    ).order_by(Room.capacity).all()
    for candidate in candidates:
        conflict = Reservation.query.filter(
            Reservation.room_id == candidate.room_id,
            Reservation.start_time < end_time_dt,
            Reservation.end_time > start_time_dt,
            Reservation.status != "cancelled"
        ).first()
        if not conflict:
            return {
                "room_id":   candidate.room_id,
                "room_name": candidate.room_name,
                "capacity":  candidate.capacity,
                "location":  candidate.location or "—",
            }
    return None


# =====================================================
# ROOMS
# =====================================================

@reservation_bp.route("/rooms", methods=["GET"])
def get_rooms():
    rooms = Room.query.all()
    return jsonify([r.to_dict() for r in rooms]), 200


# =====================================================
# RESERVATIONS
# =====================================================

@reservation_bp.route("/reservations", methods=["POST"])
def create_reservation():
    data = request.json
    try:
        user_id = int(data.get("user_id"))
        room_id = int(data.get("room_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "user_id and room_id must be integers"}), 400

    start_time = data.get("start_time")
    end_time   = data.get("end_time")

    try:
        start_time_dt = datetime.fromisoformat(start_time)
        end_time_dt   = datetime.fromisoformat(end_time)
    except Exception:
        return jsonify({"error": "Invalid datetime format"}), 400

    reservation_date = start_time_dt.date()

    if end_time_dt <= start_time_dt:
        return jsonify({"error": "End time must be after start time"}), 400

    # ── Booking rule validations ──────────────────────────────
    now = datetime.utcnow()

    # Rule 1: Must book at least 3 hours in advance
    min_start = now + timedelta(hours=3)
    if start_time_dt < min_start:
        return jsonify({
            "error": f"Bookings must be made at least 3 hours in advance. "
                     f"Earliest allowed start time is {min_start.strftime('%Y-%m-%d %H:%M')} UTC."
        }), 400

    # Rule 4: Cannot book more than 7 days in advance
    max_start = now + timedelta(days=7)
    if start_time_dt > max_start:
        return jsonify({
            "error": f"You can only book up to 7 days in advance. "
                     f"Latest allowed start date is {max_start.strftime('%Y-%m-%d')}."
        }), 400

    # Rule 2: Maximum booking duration is 6 hours
    duration_hours = (end_time_dt - start_time_dt).total_seconds() / 3600
    if duration_hours > 6:
        return jsonify({
            "error": f"Maximum booking duration is 6 hours. "
                     f"Your selected duration is {duration_hours:.1f} hours."
        }), 400

    # Rule 3: Cannot book in the past
    if start_time_dt < now:
        return jsonify({"error": "Cannot book a room in the past."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    room = Room.query.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    existing = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.start_time < end_time_dt,
        Reservation.end_time > start_time_dt,
        Reservation.status != "cancelled"
    ).first()

    if existing:
        if user.role == "staff" and existing.user.role == "student":
            override = OverrideRequest(
                reservation_id=existing.reservation_id,
                lecturer_id=user.user_id,
                student_id=existing.user_id,
                status="pending"
            )
            db.session.add(override)
            db.session.flush()
            db.session.add(Notification(
                user_id=existing.user_id,
                message=(
                    f"⚠️ Override Request: {user.full_name} (Lecturer) has requested your booking "
                    f"for {room.room_name} on {reservation_date} "
                    f"({start_time_dt.strftime('%H:%M')} - {end_time_dt.strftime('%H:%M')}). "
                    f"An admin will review this request."
                ),
                is_read=False
            ))
            db.session.commit()
            return jsonify({
                "message": (
                    f"Override request submitted. The student ({existing.user.full_name}) "
                    "has been notified and an admin will review it."
                ),
                "override_request_id": override.request_id
            }), 200
        else:
            # Feature 3: smart suggestion + Feature 15: show queue option
            suggestion = _suggest_alternative(room_id, start_time_dt, end_time_dt)

            queue_count = RoomWaitlist.query.filter_by(
                room_id=room_id,
                reservation_date=reservation_date,
                status="waiting"
            ).filter(
                RoomWaitlist.start_time == start_time_dt,
                RoomWaitlist.end_time   == end_time_dt
            ).count()

            response = {
                "error": "Room already booked for this time",
                "show_queue": True,
                "queue_count": queue_count,
                "queue_message": (
                    f"{queue_count} person(s) already in the queue. Join to secure your spot!"
                    if queue_count > 0
                    else "Be the first in the queue for this slot!"
                )
            }
            if suggestion:
                response["suggestion"] = suggestion
                response["suggestion_message"] = (
                    f"{suggestion['room_name']} is available for this slot "
                    f"(capacity: {suggestion['capacity']}). Want to book it instead?"
                )
            return jsonify(response), 400

    reservation = Reservation(
        user_id=user_id,
        room_id=room_id,
        reservation_date=reservation_date,
        start_time=start_time_dt,
        end_time=end_time_dt,
        status="pending" if user.role in ["student", "staff"] else "approved"
    )
    db.session.add(reservation)
    db.session.commit()

    return jsonify({
        "message": "Reservation created successfully",
        "reservation": reservation.to_dict()
    }), 201


@reservation_bp.route("/reservations", methods=["GET"])
def get_reservations():
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reservations]), 200


@reservation_bp.route("/reservations/user/<int:user_id>", methods=["GET"])
def get_user_reservations(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    reservations = Reservation.query.filter_by(user_id=user_id)\
        .order_by(Reservation.start_time.desc()).all()
    return jsonify([r.to_dict() for r in reservations]), 200


@reservation_bp.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"error": "Reservation not found"}), 404
    if reservation.status == "cancelled":
        return jsonify({"error": "Already cancelled"}), 400

    reservation.status = "cancelled"
    db.session.commit()

    db.session.add(Notification(
        user_id=reservation.user_id,
        message=(
            f"❌ Your reservation for {reservation.room.room_name} on "
            f"{reservation.reservation_date} "
            f"({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}) "
            f"has been cancelled."
        ),
        is_read=False
    ))
    _notify_waitlist_and_watchers(reservation)
    db.session.commit()

    return jsonify({"message": "Reservation cancelled, watchers and waitlist notified"}), 200


@reservation_bp.route("/reservations/<int:reservation_id>/approve", methods=["POST"])
def approve_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"error": "Reservation not found"}), 404
    reservation.status = "approved"
    db.session.commit()
    db.session.add(Notification(
        user_id=reservation.user_id,
        message=(
            f"✅ Approved: Your reservation for {reservation.room.room_name} on "
            f"{reservation.reservation_date} "
            f"({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}) "
            f"has been approved."
        ),
        is_read=False
    ))
    db.session.commit()
    return jsonify({"message": "Reservation approved"}), 200


@reservation_bp.route("/reservations/<int:reservation_id>/reject", methods=["POST"])
def reject_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"error": "Reservation not found"}), 404
    reservation.status = "rejected"
    db.session.commit()
    db.session.add(Notification(
        user_id=reservation.user_id,
        message=(
            f"❌ Rejected: Your reservation for {reservation.room.room_name} on "
            f"{reservation.reservation_date} "
            f"({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}) "
            f"has been rejected by admin."
        ),
        is_read=False
    ))
    db.session.commit()
    return jsonify({"message": "Reservation rejected"}), 200


# =====================================================
# USERS
# =====================================================

@reservation_bp.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@reservation_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


@reservation_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
def toggle_user_active(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({
        "message": f"User {'activated' if user.is_active else 'deactivated'}",
        "is_active": user.is_active
    }), 200


# =====================================================
# OVERRIDE REQUESTS
# =====================================================

@reservation_bp.route("/override-requests", methods=["GET"])
def get_override_requests():
    overrides = OverrideRequest.query.order_by(OverrideRequest.created_at.desc()).all()
    result = []
    for o in overrides:
        d = o.to_dict()
        lecturer    = User.query.get(o.lecturer_id)
        student     = User.query.get(o.student_id)
        reservation = Reservation.query.get(o.reservation_id)
        d["lecturer_name"] = lecturer.full_name  if lecturer    else "Unknown"
        d["student_name"]  = student.full_name   if student     else "Unknown"
        d["room_name"]     = reservation.room.room_name if reservation and reservation.room else "Unknown"
        d["start_time"]    = str(reservation.start_time) if reservation else "—"
        d["end_time"]      = str(reservation.end_time)   if reservation else "—"
        result.append(d)
    return jsonify(result), 200


@reservation_bp.route("/override-requests/<int:request_id>/accept", methods=["POST"])
def accept_override(request_id):
    override = OverrideRequest.query.get(request_id)
    if not override:
        return jsonify({"error": "Override request not found"}), 404

    override.status = "accepted"
    student_reservation = Reservation.query.get(override.reservation_id)
    lecturer            = User.query.get(override.lecturer_id)

    if not student_reservation:
        return jsonify({"error": "Original reservation not found"}), 404

    # 1. Cancel the student's reservation
    student_reservation.status = "cancelled"
    db.session.add(Notification(
        user_id=override.student_id,
        message=(
            f"⚠️ Your reservation #{student_reservation.reservation_id} for "
            f"{student_reservation.room.room_name} on {student_reservation.reservation_date} "
            f"({student_reservation.start_time.strftime('%H:%M')} - {student_reservation.end_time.strftime('%H:%M')}) "
            f"has been overridden by {lecturer.full_name if lecturer else 'a lecturer'} and cancelled."
        ),
        is_read=False
    ))

    # 2. Create a new APPROVED reservation for the lecturer/staff
    staff_reservation = Reservation(
        user_id=override.lecturer_id,
        room_id=student_reservation.room_id,
        reservation_date=student_reservation.reservation_date,
        start_time=student_reservation.start_time,
        end_time=student_reservation.end_time,
        status="approved"
    )
    db.session.add(staff_reservation)
    db.session.flush()  # flush so staff_reservation.reservation_id is available

    # 3. Notify the staff with their new reservation ID
    if lecturer:
        db.session.add(Notification(
            user_id=override.lecturer_id,
            message=(
                f"✅ Your override request was accepted! A new reservation has been created for you. "
                f"Reservation #{staff_reservation.reservation_id} — "
                f"{student_reservation.room.room_name} on {student_reservation.reservation_date} "
                f"({student_reservation.start_time.strftime('%H:%M')} - {student_reservation.end_time.strftime('%H:%M')}). "
                f"Check your My Reservations page."
            ),
            is_read=False
        ))

    # 4. Notify waitlist/watchers that the slot briefly opened then was taken
    _notify_waitlist_and_watchers(student_reservation)

    db.session.commit()
    return jsonify({
        "message": "Override accepted",
        "staff_reservation_id": staff_reservation.reservation_id
    }), 200


@reservation_bp.route("/override-requests/<int:request_id>/reject", methods=["POST"])
def reject_override(request_id):
    override = OverrideRequest.query.get(request_id)
    if not override:
        return jsonify({"error": "Override request not found"}), 404

    override.status = "rejected"
    reservation = Reservation.query.get(override.reservation_id)
    lecturer    = User.query.get(override.lecturer_id)

    if lecturer and reservation:
        db.session.add(Notification(
            user_id=override.lecturer_id,
            message=(
                f"❌ Your override request for {reservation.room.room_name} on "
                f"{reservation.reservation_date} has been rejected. "
                f"The student's booking remains active."
            ),
            is_read=False
        ))

    db.session.commit()
    return jsonify({"message": "Override rejected"}), 200


# =====================================================
# NOTIFICATIONS
# =====================================================

@reservation_bp.route("/notifications/user/<int:user_id>", methods=["GET"])
def get_user_notifications(user_id):
    notifications = Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications]), 200


@reservation_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    notif = Notification.query.get(notification_id)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 13 — BOOKING REMINDERS
# POST /notifications/send-reminders
# Sends  reminders for approved bookings starting within 30 minutes.
# Call via cron / APScheduler every 5 minutes:
#   from apscheduler.schedulers.background import BackgroundScheduler
#   scheduler = BackgroundScheduler()
#   scheduler.add_job(lambda: requests.post("http://127.0.0.1:5000/notifications/send-reminders"), 'interval', minutes=5)
#   scheduler.start()
# ─────────────────────────────────────────────────────────────────────────────

@reservation_bp.route("/notifications/send-reminders", methods=["POST"])
def send_reminders():
    now    = datetime.utcnow()
    window = now + timedelta(minutes=30)

    upcoming = Reservation.query.filter(
        Reservation.status == "approved",
        Reservation.start_time >= now,
        Reservation.start_time <= window
    ).all()

    sent = 0
    for res in upcoming:
        already = Notification.query.filter(
            Notification.user_id == res.user_id,
            Notification.message.like(f"%⏰%Reminder%#{res.reservation_id}%")
        ).first()
        if already:
            continue
        minutes_left = int((res.start_time - now).total_seconds() / 60)
        db.session.add(Notification(
            user_id=res.user_id,
            message=(
                f"⏰ Reminder (#{res.reservation_id}): Your booking for "
                f"{res.room.room_name} starts in {minutes_left} minutes "
                f"({res.start_time.strftime('%H:%M')} - {res.end_time.strftime('%H:%M')}). "
                f"Don't forget!"
            ),
            is_read=False
        ))
        sent += 1

    db.session.commit()
    return jsonify({"message": f"Reminders sent: {sent}"}), 200


# =====================================================
# WATCHLIST
# =====================================================

@reservation_bp.route("/watchlist", methods=["GET"])
def get_watchlist():
    items = RoomWatchlist.query.order_by(RoomWatchlist.created_at.desc()).all()
    result = []
    for w in items:
        d = w.to_dict()
        user = User.query.get(w.user_id)
        room = Room.query.get(w.room_id)
        d["user_name"] = user.full_name if user else "Unknown"
        d["room_name"] = room.room_name if room else "Unknown"
        d["start_time"] = str(w.start_time)
        d["end_time"]   = str(w.end_time)
        result.append(d)
    return jsonify(result), 200


@reservation_bp.route("/watchlist", methods=["POST"])
def add_to_watchlist():
    data = request.json
    try:
        user_id = int(data.get("user_id"))
        room_id = int(data.get("room_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "user_id and room_id must be integers"}), 400

    start_time = data.get("start_time")
    end_time   = data.get("end_time")

    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt   = datetime.fromisoformat(end_time)
    except Exception:
        return jsonify({"error": "Invalid datetime format"}), 400

    existing = RoomWatchlist.query.filter_by(
        user_id=user_id, room_id=room_id
    ).filter(
        RoomWatchlist.start_time == start_dt,
        RoomWatchlist.end_time   == end_dt
    ).first()

    if existing:
        return jsonify({"error": "Already watching this slot"}), 400

    watch = RoomWatchlist(
        user_id=user_id,
        room_id=room_id,
        reservation_date=start_dt.date(),
        start_time=start_dt,
        end_time=end_dt
    )
    db.session.add(watch)
    db.session.commit()
    return jsonify({"message": "Added to watchlist", "watch_id": watch.watch_id}), 201


@reservation_bp.route("/watchlist/user/<int:user_id>", methods=["GET"])
def get_user_watchlist(user_id):
    items = RoomWatchlist.query.filter_by(user_id=user_id)\
        .order_by(RoomWatchlist.created_at.desc()).all()
    result = []
    for w in items:
        d = w.to_dict()
        room = Room.query.get(w.room_id)
        d["room_name"] = room.room_name if room else "Unknown"
        d["start_time"] = str(w.start_time)
        d["end_time"]   = str(w.end_time)
        result.append(d)
    return jsonify(result), 200


@reservation_bp.route("/watchlist/<int:watch_id>", methods=["DELETE"])
def remove_from_watchlist(watch_id):
    watch = RoomWatchlist.query.get(watch_id)
    if not watch:
        return jsonify({"error": "Watchlist entry not found"}), 404
    db.session.delete(watch)
    db.session.commit()
    return jsonify({"message": "Removed from watchlist"}), 200


# =====================================================
# FEATURE 15 — WAITLIST QUEUE
# =====================================================

@reservation_bp.route("/waitlist/join", methods=["POST"])
def join_waitlist():
    data = request.json
    try:
        user_id = int(data.get("user_id"))
        room_id = int(data.get("room_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "user_id and room_id must be integers"}), 400

    start_time = data.get("start_time")
    end_time   = data.get("end_time")

    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt   = datetime.fromisoformat(end_time)
    except Exception:
        return jsonify({"error": "Invalid datetime format"}), 400

    existing = RoomWaitlist.query.filter_by(
        user_id=user_id, room_id=room_id, status="waiting"
    ).filter(
        RoomWaitlist.start_time == start_dt,
        RoomWaitlist.end_time   == end_dt
    ).first()
    if existing:
        return jsonify({
            "error": "Already in queue",
            "queue_position": existing.queue_position
        }), 400

    last = RoomWaitlist.query.filter_by(
        room_id=room_id, status="waiting"
    ).filter(
        RoomWaitlist.start_time == start_dt,
        RoomWaitlist.end_time   == end_dt
    ).order_by(RoomWaitlist.queue_position.desc()).first()

    next_position = (last.queue_position + 1) if last else 1
    room = Room.query.get(room_id)

    entry = RoomWaitlist(
        user_id=user_id,
        room_id=room_id,
        reservation_date=start_dt.date(),
        start_time=start_dt,
        end_time=end_dt,
        queue_position=next_position,
        status="waiting"
    )
    db.session.add(entry)
    db.session.add(Notification(
        user_id=user_id,
        message=(
            f"📋 Waitlist Joined: You are #{next_position} in the queue for "
            f"{room.room_name if room else 'this room'} on {start_dt.date()} "
            f"({start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}). "
            f"We'll notify you when it's your turn!"
        ),
        is_read=False
    ))
    db.session.commit()

    return jsonify({
        "message": f"Joined waitlist at position #{next_position}",
        "waitlist_id":    entry.waitlist_id,
        "queue_position": next_position
    }), 201


@reservation_bp.route("/waitlist/user/<int:user_id>", methods=["GET"])
def get_user_waitlist(user_id):
    items = RoomWaitlist.query.filter_by(user_id=user_id)\
        .order_by(RoomWaitlist.created_at.desc()).all()
    result = []
    for w in items:
        d = w.to_dict()
        room = Room.query.get(w.room_id)
        d["room_name"] = room.room_name if room else "Unknown"
        result.append(d)
    return jsonify(result), 200


@reservation_bp.route("/waitlist/<int:waitlist_id>", methods=["DELETE"])
def leave_waitlist(waitlist_id):
    entry = RoomWaitlist.query.get(waitlist_id)
    if not entry:
        return jsonify({"error": "Waitlist entry not found"}), 404

    room_id     = entry.room_id
    start_time  = entry.start_time
    end_time    = entry.end_time
    removed_pos = entry.queue_position

    db.session.delete(entry)

    # Shift queue positions up for everyone behind
    behind = RoomWaitlist.query.filter_by(
        room_id=room_id, status="waiting"
    ).filter(
        RoomWaitlist.start_time == start_time,
        RoomWaitlist.end_time   == end_time,
        RoomWaitlist.queue_position > removed_pos
    ).all()
    for e in behind:
        e.queue_position -= 1

    db.session.commit()
    return jsonify({"message": "Left the waitlist"}), 200


@reservation_bp.route("/waitlist", methods=["GET"])
def get_all_waitlist():
    """Admin view — all waitlist entries grouped by room and slot."""
    items = RoomWaitlist.query.order_by(
        RoomWaitlist.room_id,
        RoomWaitlist.start_time,
        RoomWaitlist.queue_position
    ).all()
    result = []
    for w in items:
        d = w.to_dict()
        user = User.query.get(w.user_id)
        room = Room.query.get(w.room_id)
        d["user_name"] = user.full_name if user else "Unknown"
        d["room_name"] = room.room_name if room else "Unknown"
        result.append(d)
    return jsonify(result), 200