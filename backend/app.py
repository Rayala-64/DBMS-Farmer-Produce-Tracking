from flask import Flask, request, redirect, session, render_template, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
from flask import url_for

# ---------------- APP CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "dbms_project_secret_key"

# ---------------- DATABASE ----------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="flaskuser",
        password="flask@123",
        database="agriculture",
        auth_plugin="mysql_native_password"
    )

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    email = request.form.get("email")
    raw_password = request.form.get("password")
    role = request.form.get("role")

    # Validation
    if not all([name, email, raw_password, role]):
        flash("All fields are required", "danger")
        return redirect('/register')

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email format", "danger")
        return redirect('/register')

    if len(raw_password) < 6:
        flash("Password must be at least 6 characters", "warning")
        return redirect('/register')
    
    hashed_password = generate_password_hash(raw_password)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, hashed_password, role)
        )
        conn.commit()

        user_id = cur.lastrowid  # 🔥 important

        if role == "Farmer":
            cur.execute(
                """
                INSERT INTO farmers (user_id, farmer_name, contact_no)
                VALUES (%s, %s, %s)
                """,
                (user_id, name, "NOT_PROVIDED")
            )
        conn.commit()
        flash("Registration successful. Please login.", "success")
        return redirect('/login')
    
    except mysql.connector.IntegrityError:
        flash("Email already registered", "danger")
    
    finally:
        cur.close()
        conn.close()

    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Email and password are required", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT user_id, password, role
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cur.fetchone()

    if not user or not check_password_hash(user["password"], password):
        cur.close()
        conn.close()
        flash("Invalid email or password", "danger")
        return redirect(url_for("login"))

    # ---------------- SESSION SETUP ----------------
    session.clear()
    user_id = user["user_id"]
    role = user["role"].lower()   # normalize once

    session["user_id"] = user_id
    session["role"] = role

    # ---------------- FARMER PROFILE FAILSAFE ----------------
    if role == "farmer":
        cur.execute(
            "SELECT farmer_id FROM farmers WHERE user_id = %s",
            (user_id,)
        )
        farmer = cur.fetchone()

        if not farmer:
            cur.execute(
                """
                INSERT INTO farmers (user_id, farmer_name, contact_no)
                VALUES (%s, %s, %s)
                """,
                (user_id, "UNKNOWN", "NOT_PROVIDED")
            )
            conn.commit()

    cur.close()
    conn.close()

    flash("Login successful", "success")

    role_route_map = {
        "farmer": "/farmer/dashboard",
        "retailer": "/retailer/dashboard",
        "warehouse manager": "/warehouse/dashboard",
        "logistics operator": "/logistics/dashboard"
    }

    return redirect(role_route_map[role])

  

# ---------------- DASHBOARDS ----------------
@app.route("/farmer/dashboard")
def farmer_dashboard():
    if session.get('role') != 'farmer':
        flash("Unauthorized access", "danger")
        return redirect(url_for("login"))
    
    return render_template('farmer/farmer_dashboard.html')

@app.route("/farmer/add-produce", methods=["GET", "POST"])
def add_produce():
    if session.get("role") != "farmer":
        flash("Unauthorized access", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        user_id = session["user_id"]

        crop = request.form["crop_name"]
        quantity = request.form["quantity"]
        quality = request.form["quality"]
        harvest_date = request.form["harvest_date"]

        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        # get farmer_id using user_id
        cur.execute(
            "SELECT farmer_id FROM farmers WHERE user_id = %s",
            (user_id,)
        )
        farmer = cur.fetchone()

        if not farmer:
            flash("Farmer profile not found", "danger")
            return redirect(url_for("farmer_dashboard"))

        farmer_id = farmer["farmer_id"]

        cur.execute(
            """
            INSERT INTO produce (farmer_id, crop_name, quantity, quality, harvest_date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (farmer_id, crop, quantity, quality, harvest_date)
        )

        db.commit()
        cur.close()
        db.close()

        flash("Produce added successfully", "success")
        return redirect(url_for("farmer_dashboard"))

    return render_template("farmer/add_produce.html")


@app.route("/farmer/view-produce")
def view_produce():
    return render_template("farmer/view_produce.html")


@app.route("/retailer/dashboard")
def retailer_dashboard():
    if 'user_id' not in session or session.get('role') != 'Retailer':
        flash("Unauthorized access", "danger")
        return redirect('/login')
    return render_template('retailer/retailer_dashboard.html')

@app.route("/warehouse/dashboard")
def warehouse_dashboard():
    if 'user_id' not in session or session.get('role') != 'Warehouse Manager':
        flash("Unauthorized access", "danger")
        return redirect('/login')
    return render_template('warehouse/warehouse_dashboard.html')

@app.route("/logistics/dashboard")
def logistics_dashboard():
    if 'user_id' not in session or session.get('role') != 'Logistics Operator':
        flash("Unauthorized access", "danger")
        return redirect('/login')
    return render_template('logistics/logistics_dashboard.html')

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
