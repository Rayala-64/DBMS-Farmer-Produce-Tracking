from flask import Flask, request, redirect, session, render_template
import mysql.connector
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = "dbms_project_secret_key"


# ---------- DATABASE ----------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="flaskuser",
        password="flask@123",
        database="agriculture",
        auth_plugin="mysql_native_password"
    )


# ---------- HOME ----------
@app.route('/')
def home():
    return render_template('index.html')


# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if not all([name, email, password, role]):
        return "All fields are required"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (%s, %s, %s, %s)
        """, (name, email, password, role))
        conn.commit()
    except mysql.connector.IntegrityError:
        return "Email already registered"
    finally:
        cur.close()
        conn.close()

    return redirect('/login')


# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return "Email and password are required"

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT user_id, role
        FROM users
        WHERE email = %s AND password = %s
    """, (email, password))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        session['user_id'] = user['user_id']
        session['role'] = user['role']

        role_route_map = {
            'Farmer': 'farmer',
            'Retailer': 'retailer',
            'Warehouse Manager': 'warehouse',
            'Logistics Operator': 'logistics'
        }

        return redirect(f"/{role_route_map[user['role']]}/dashboard")

    return "Invalid email or password"


# ---------- DASHBOARDS ----------
@app.route('/warehouse/dashboard')
def warehouse_dashboard():
    if session.get('role') != 'Warehouse Manager':
        return redirect('/login')
    return render_template('warehouse/warehouse_dashboard.html')


@app.route('/retailer/dashboard')
def retailer_dashboard():
    if session.get('role') != 'Retailer':
        return redirect('/login')
    return render_template('retailer/retailer_dashboard.html')


@app.route('/farmer/dashboard')
def farmer_dashboard():
    if session.get('role') != 'Farmer':
        return redirect('/login')
    return render_template('farmer/farmer_dashboard.html')


@app.route('/logistics/dashboard')
def logistics_dashboard():
    if session.get('role') != 'Logistics Operator':
        return redirect('/login')
    return render_template('logistics/logistics_dashboard.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)

print("TEMPLATES DIR:", app.template_folder)
print("STATIC DIR:", app.static_folder)