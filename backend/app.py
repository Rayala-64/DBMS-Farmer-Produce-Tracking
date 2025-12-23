from flask import Flask, request, redirect, session, render_template, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

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
        flash("Registration successful. Please login.", "success")
        return redirect('/login')
    
    except mysql.connector.IntegrityError:
        flash("Email already registered", "danger")
    
    finally:
        cur.close()
        conn.close()

    return redirect("/login")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Email and password are required", "danger")
        return redirect('/login')

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
    cur.close()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        print("ROLE FROM DB:", user["role"])

        flash("Login successful", "success")

        role_route_map = {
            "Farmer": "/farmer/dashboard",
            "Retailer": "/retailer/dashboard",
            "Warehouse Manager": "/warehouse/dashboard",
            "Logistics Operator": "/logistics/dashboard"
        }

        return redirect(role_route_map[user["role"]])

    flash("Invalid email or password", "danger")
    print("FORM DATA:", request.form)
    return redirect('/login')
  



# ---------------- DASHBOARDS ----------------
@app.route("/farmer/dashboard")
def farmer_dashboard():
    if 'user_id' not in session or session.get('role') != 'Farmer':
        flash("Unauthorized access", "danger")
        return redirect('/login')
    return render_template('farmer/farmer_dashboard.html')

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
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
