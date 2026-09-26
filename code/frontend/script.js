
const BASE_URL = "http://127.0.0.1:5000";

/* Current Status */
function loadStatus() {
    fetch(BASE_URL + "/rooms/current-status") /* Sends an HTTP GET request to the backend */
    .then(res => res.json()) /* convert the JSON response into a javascript object*/
    .then(data => {
        const div = document.getElementById("status"); /* Finds the HTML element whose id is "status" */
        if (!div) return;

        div.innerHTML = ""; /* Clear previous results*/

        data.forEach(room => { /* Loop through every room returmd from the backend */
            const card = document.createElement("div");
            card.className = "card";

            if (room.status === "Occupied") {
                card.innerHTML =
                    room.room_name +
                    " - <span class='occupied'>Occupied</span> (" +
                    room.booked_from + " - " +
                    room.booked_to + ")";
            } else {
                card.innerHTML =
                    room.room_name +
                    " - <span class='free'>Free</span>";
            }

            div.appendChild(card); /* Adds the card into webpage*/
        });
    });
}

/* Daily Schedule */
function loadSchedule() {
    const date = document.getElementById("dateInput").value;

    fetch(BASE_URL + "/rooms/schedule?date=" + date)
    .then(res => res.json())
    .then(data => {
        const div = document.getElementById("schedule");
        if (!div) return;

        div.innerHTML = "";

        data.forEach(room => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = "<h3>" + room.room_name + "</h3>";

            if (room.bookings.length === 0) {
                card.innerHTML += "<p>No bookings</p>";
            } else {
                room.bookings.forEach(b => {
                    card.innerHTML +=
                        "<p>" + b.start + " - " + b.end + "</p>";
                });
            }

            div.appendChild(card);
        });
    });
}

/* Search Room */
function searchRoom() {
    const name = document.getElementById("searchName").value;
    const date = document.getElementById("searchDate").value;

    fetch(BASE_URL + "/rooms/search?name=" + name + "&date=" + date)
    .then(res => res.json())
    .then(data => {
        const div = document.getElementById("searchResult");
        if (!div) return;

        div.innerHTML = "";

        data.forEach(room => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = "<h3>" + room.room_name + "</h3>";

            room.bookings.forEach(b => {
                card.innerHTML +=
                    "<p>" + b.start + " - " + b.end + "</p>";
            });

            div.appendChild(card);
        });
    });
}

/* Availability */
function checkAvailability() {
    const roomId = document.getElementById("roomId").value;
    const date = document.getElementById("availDate").value;

    fetch(BASE_URL + "/rooms/availability?room_id=" + roomId + "&date=" + date)
    .then(res => res.json())
    .then(data => {
        const div = document.getElementById("availability");
        if (!div) return;

        div.innerHTML = "";

        if (data.free_slots.length === 0) {
            div.innerHTML = "<p>No free slots</p>";
            return;
        }

        data.free_slots.forEach(slot => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML =
                "Free: " + slot.start + " - " + slot.end;
            div.appendChild(card);
        });
    });
  }
/* ============================================================
   ChronoCampus — script.js
   Auth pages: signup + login
   Saves session to sessionStorage → redirects to dashboard.html
   ============================================================ */

const backendURL = "http://127.0.0.1:5000";

/* ── Message helper ───────────────────────────────────────── */
function setMessage(elId, msg, type) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.textContent = (type === "error" ? "⚠ " : "✓ ") + msg;
  el.className   = type; // triggers CSS colour
}

/* ── SIGNUP ───────────────────────────────────────────────── */
const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", async function(e) {
    e.preventDefault();
    const btn = signupForm.querySelector("button[type=submit]");
    btn.disabled    = true;
    btn.textContent = "Creating account…";

    const data = {
      full_name:  document.getElementById("full_name").value.trim(),
      email:      document.getElementById("email").value.trim(),
      password:   document.getElementById("password").value,
      department: document.getElementById("department").value
    };

    try {
      const response = await fetch(`${backendURL}/auth/register`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(data)
      });

      const result = await response.json();

      if (!response.ok) {
        setMessage("message", result.error || "Registration failed", "error");
        btn.disabled    = false;
        btn.textContent = "Register";
        return;
      }

      setMessage("message", result.message || "Account created! Redirecting…", "success");
      setTimeout(() => window.location.href = "/login", 1500);

    } catch {
      setMessage("message", "Cannot connect to server. Is Flask running?", "error");
      btn.disabled    = false;
      btn.textContent = "Register";
    }
  });
}

/* ── LOGIN ────────────────────────────────────────────────── */
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async function(e) {
    e.preventDefault();
    const btn = loginForm.querySelector("button[type=submit]");
    btn.disabled    = true;
    btn.textContent = "Signing in…";

    const data = {
      email:    document.getElementById("login_email").value.trim(),
      password: document.getElementById("login_password").value
    };

    try {
      const response = await fetch(`${backendURL}/auth/login`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(data),
        credentials: "include"
      });

      if (!response.ok) {
        const err = await response.json();
        setMessage("loginMessage", err.error || "Login failed", "error");
        btn.disabled    = false;
        btn.textContent = "Login";
        return;
      }

      const result = await response.json();
      const user   = result.user;

      // ── Save session to sessionStorage (tab-isolated) ──────
      sessionStorage.setItem("user_id",   user.user_id);
      sessionStorage.setItem("role",      user.role);
      sessionStorage.setItem("user_name", user.full_name);
      sessionStorage.setItem("email",     user.email);

      setMessage("loginMessage", "Login successful! Redirecting…", "success");

      // ── Go to dashboard.html — it redirects by role ────────
      setTimeout(() => window.location.href = "/dashboard", 800);

    } catch {
      setMessage("loginMessage", "Cannot connect to server. Is Flask running?", "error");
      btn.disabled    = false;
      btn.textContent = "Login";
    }
  });
}
/* ── CHANGE PASSWORD ──────────────────────────────────────── */
const changePasswordForm = document.getElementById("changePasswordForm");
if (changePasswordForm) {
  changePasswordForm.addEventListener("submit", async function(e) {
    e.preventDefault();
    const btn = changePasswordForm.querySelector("button[type=submit]");
    btn.disabled    = true;
    btn.textContent = "Updating…";

    const data = {
      email:        document.getElementById("cp_email").value.trim(),
      old_password: document.getElementById("old_password").value,
      new_password: document.getElementById("new_password").value
    };

    try {
      const response = await fetch(`${backendURL}/auth/change-password`, {
        method:  "PUT",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(data),
        credentials: "include"
      });

      const result = await response.json();

      if (!response.ok) {
        setMessage("changePasswordMessage", result.error || "Failed to change password", "error");
        btn.disabled    = false;
        btn.textContent = "Change Password";
        return;
      }

      setMessage("changePasswordMessage", result.message || "Password changed! Redirecting to login…", "success");
      changePasswordForm.reset();

      setTimeout(() => window.location.href = "/login", 1500);

    } catch {
      setMessage("changePasswordMessage", "Cannot connect to server. Is Flask running?", "error");
      btn.disabled    = false;
      btn.textContent = "Change Password";
    }
  });
}