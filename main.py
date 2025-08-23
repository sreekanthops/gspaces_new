import os
import random
import string
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor # Import RealDictCursor

# Flask imports
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, make_response, send_from_directory
)
from werkzeug.utils import secure_filename

# Flask-Login imports
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user, UserMixin
)

# Google OAuth imports
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from authlib.integrations.flask_client import OAuth

# Email imports
from flask_mail import Mail, Message

# Password reset imports
from itsdangerous import URLSafeTimedSerializer

# Payment gateway imports
import razorpay

# Datetime import
from datetime import datetime

# --- CONFIGURATION ---
# Read from environment variables if available; fallback to development defaults.
# IMPORTANT: In production, NEVER hardcode sensitive information like this.
# Use environment variables (e.g., FLASK_APP_SECRET_KEY, DB_PASSWORD, RAZORPAY_KEY_ID)
# or a proper configuration management system.

# Flask App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_APP_SECRET_KEY', 'your_super_secret_fallback_key') # Replace with a strong, random key
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true' # True in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your_email@gmail.com') # Your email for sending
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your_email_app_password') # Your app password
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'your_email@gmail.com')

mail = Mail(app)

# Serializer for password reset (uses app.config['SECRET_KEY'])
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "226581903418-3ed1eqsl14qlou4nmk2m9sdf6il1mluu.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")

# Admin Emails (for simple admin check)
ADMIN_EMAILS = {"admin@example.com", "another_admin@example.com"} # Replace with actual admin emails

# Database Configuration
DB_NAME = os.getenv("DB_NAME", "gspaces")
DB_USER = os.getenv("DB_USER", "sri")
DB_PASSWORD = os.getenv("DB_PASSWORD", "gspaces2025")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# File Uploads Configuration
UPLOAD_FOLDER = os.path.join('static', 'img', 'Products')
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Ensure directory exists
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_R6wg6buSedSnTV") # Test Key ID
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "xeBC7q5tEirlDg4y4Tc3JEc3") # Test Key Secret

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# --- FLASK-LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # The endpoint name for the login page

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name, is_admin=False):
        self.id = id
        self.email = email
        self.name = name
        self.is_admin = is_admin # Add is_admin attribute

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = None
    try:
        conn = connect_to_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, email, name FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            # Check if the user's email is in ADMIN_EMAILS to set is_admin
            is_admin = user_data['email'] in ADMIN_EMAILS
            return User(id=user_data['id'], email=user_data['email'], name=user_data['name'], is_admin=is_admin)
        else:
            return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
    finally:
        if conn:
            conn.close()

# --- GOOGLE OAUTH SETUP ---
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# --- DATABASE HELPERS ---
def connect_to_db():
    try:
        conn = psycopg2.connect(
            database=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        return conn
    except Error as e:
        print(f"DB connection error: {e}")
        return None

def create_users_table(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                address VARCHAR(255),
                phone VARCHAR(50)
            );
        """)
        conn.commit()
    except Error as e:
        print(f"Error creating users table: {e}")

def create_products_table(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100),
                price DECIMAL(10, 2),
                rating DECIMAL(2, 1),
                image_url VARCHAR(255),
                created_by VARCHAR(255)
            );
        """)
        conn.commit()
    except Error as e:
        print(f"Error creating products table: {e}")

def create_reviews_table(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                username VARCHAR(255),
                rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    except Error as e:
        print(f"Error creating reviews table: {e}")

def create_orders_table(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL,
                razorpay_order_id VARCHAR(255) UNIQUE NOT NULL,
                razorpay_payment_id VARCHAR(255),
                total_amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    except Error as e:
        print(f"Error creating orders table: {e}")

def create_order_items_table(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id),
                product_name VARCHAR(255) NOT NULL,
                quantity INTEGER NOT NULL,
                price_at_purchase DECIMAL(10, 2) NOT NULL,
                image_url VARCHAR(255)
            );
        """)
        conn.commit()
    except Error as e:
        print(f"Error creating order_items table: {e}")


# --- UTILITY FUNCTIONS ---
@app.template_filter('inr')
def inr_format(value):
    try:
        return f"{float(value):.2f}"
    except:
        return value

def upsert_user_from_google(google_sub, name, email):
    """Insert user if missing; return (id, name, email)."""
    conn = connect_to_db()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, email FROM users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        if not user_data:
            # For Google users, we can use a dummy password or handle it differently
            # In a real app, you might distinguish between password and OAuth users
            dummy_password = "oauth_user_no_password_" + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            cur.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
                RETURNING id, name, email
            """, (name or email.split("@")[0], email, dummy_password))
            user_data = cur.fetchone()
            conn.commit()
        return user_data
    except Exception as e:
        print(f"upsert_user_from_google error: {e}")
        return None
    finally:
        if conn:
            cur.close()
            conn.close()

# --- ROUTES: MARKETING & LEGAL ---
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/refund')
def refund_policy():
    return render_template('refund.html')

@app.route('/shipping')
def shipping_policy():
    return render_template('shipping.html')

# --- AUTHENTICATION ROUTES (Email/Password & Google) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password') # In production, use hashed passwords!
        conn = connect_to_db()
        if not conn:
            flash("Database connection failed during login.", "error")
            return render_template('login.html')
        cur = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor
        try:
            cur.execute("SELECT id, name, email, password FROM users WHERE email = %s", (email,))
            user_data = cur.fetchone()

            if user_data and user_data['password'] == password: # Replace with check_password_hash in production
                user_obj = User(id=user_data['id'], email=user_data['email'],
                                name=user_data['name'], is_admin=(user_data['email'] in ADMIN_EMAILS))
                login_user(user_obj) # Log in the user using Flask-Login
                flash(f"Welcome, {user_data['name']}!", "success")
                return redirect(url_for('index'))
            else:
                flash("Invalid email or password", "error")
                return render_template('login.html')
        except Error as e:
            print(f"Login DB error: {e}")
            flash("An error occurred during login.", "error")
            return render_template('login.html')
        finally:
            if conn:
                cur.close()
                conn.close()
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password') # In production, use hashed passwords!

            conn = connect_to_db()
            if not conn:
                flash("Database connection failed.", "error")
                return redirect(url_for('signup'))
            cursor = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor

            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered. Please log in or use another email.", "error")
                return render_template('login.html')

            cursor.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s) RETURNING id, name, email
            """, (name, email, password)) # Password should be hashed
            new_user_data = cursor.fetchone()
            conn.commit()

            # Automatically log in the new user after signup
            if new_user_data:
                new_user_obj = User(id=new_user_data['id'], email=new_user_data['email'],
                                    name=new_user_data['name'], is_admin=(new_user_data['email'] in ADMIN_EMAILS))
                login_user(new_user_obj)
                flash("Signup successful! You have been logged in.", "success")
                return redirect(url_for('index'))
            else:
                flash("Signup failed. No user data returned after insert.", "error")
                return render_template('login.html')

        except Exception as e:
            print(f"❌ Signup error: {e}")
            flash("Signup failed due to a server error. Please try again.", "error")
            return render_template('login.html')
        finally:
            if conn:
                cursor.close()
                conn.close()
    return render_template('signup.html') # Ensure you have a signup.html template

@app.route('/logout')
@login_required
def logout():
    logout_user() # Flask-Login handles clearing the session
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# --- GOOGLE OAUTH ROUTES ---
@app.route("/login/google")
def login_google():
    redirect_uri = url_for("auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token)
        email = user_info.get("email")
        name = user_info.get("name") or (email.split("@")[0] if email else "User")

        if not email:
            flash("Google did not return an email. Cannot log you in.", "danger")
            return redirect(url_for("login"))

        # Upsert user and get their DB ID
        user_data_db = upsert_user_from_google(user_info.get('sub'), name, email)

        if user_data_db:
            user_obj = User(id=user_data_db['id'], email=user_data_db['email'],
                            name=user_data_db['name'], is_admin=(user_data_db['email'] in ADMIN_EMAILS))
            login_user(user_obj)
            flash(f"Welcome, {user_data_db['name']} (Google Login)!", "success")
            return redirect(url_for("index")) # Redirect to index or profile page
        else:
            flash("Failed to process Google login. Please try again.", "danger")
            return redirect(url_for("login"))

    except Exception as e:
        print(f"Google callback error: {e}")
        flash("Google login failed. Please try again.", "danger")
        return redirect(url_for("login"))

@app.route('/google_signin', methods=['GET', 'POST'])
def google_signin():
    # This route is typically for One Tap, which handles its own redirects or responses via JS.
    # The current implementation primarily handles the POST request from One Tap's credential response.
    if request.method == "GET":
        # If a GET request comes here, redirect to the full OAuth flow for clarity
        return redirect(url_for("login_google"))

    try:
        data = request.get_json(silent=True) or {}
        token = data.get('credential')
        if not token:
            return make_response(jsonify({"success": False, "message": "Missing credential"}), 400)

        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        if idinfo.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
            return make_response(jsonify({"success": False, "message": "Invalid issuer"}), 400)

        email = idinfo.get('email')
        name = idinfo.get('name') or (email.split("@")[0] if email else "User")
        if not email:
            return make_response(jsonify({"success": False, "message": "Email missing in token"}), 400)

        user_data_db = upsert_user_from_google(idinfo.get('sub'), name, email)

        if user_data_db:
            user_obj = User(id=user_data_db['id'], email=user_data_db['email'],
                            name=user_data_db['name'], is_admin=(user_data_db['email'] in ADMIN_EMAILS))
            login_user(user_obj)
            return jsonify({"success": True, "redirect": url_for('index')})
        else:
            return make_response(jsonify({"success": False, "message": "Failed to process user"}), 500)

    except ValueError as e:
        print(f"Google token verify error: {e}")
        return make_response(jsonify({"success": False, "message": "Invalid token"}), 400)
    except Exception as e:
        print(f"google_signin server error: {e}")
        return make_response(jsonify({"success": False, "message": "Server error"}), 500)

# --- PASSWORD RESET ROUTES ---
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        conn = None
        try:
            conn = connect_to_db()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            if user:
                token = s.dumps(email, salt='password-reset-salt')
                reset_url = url_for('reset_password', token=token, _external=True)

                msg = Message('Password Reset Request for GSpaces', recipients=[email])
                msg.body = f'''Hi,\n\nTo reset your password, click the link below:\n{reset_url}\n\nIf you didn’t request this, please ignore.\n\nRegards,\nGSpaces Team\n'''
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'success')
            else:
                flash('No account found with that email address.', 'danger')
        except Exception as e:
            print(f"Forgot password error: {e}")
            flash('An error occurred while processing your request.', 'error')
        finally:
            if conn:
                cur.close()
                conn.close()
    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600) # Token valid for 1 hour
    except Exception:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return render_template('reset_password.html', token=token) # Stay on the reset page

        conn = None
        try:
            conn = connect_to_db()
            cur = conn.cursor()
            # IMPORTANT: In production, hash the new_password before updating!
            cur.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
            conn.commit()
            flash('Your password has been reset successfully. Please log in with your new password.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Reset password DB error: {e}")
            flash('An error occurred while resetting your password.', 'error')
        finally:
            if conn:
                cur.close()
                conn.close()

    return render_template('reset_password.html', token=token)

# --- HOME ROUTE ---
@app.route('/')
def index():
    conn = connect_to_db()
    product_list = []
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor
            cursor.execute("""
                SELECT id, name, description, category, price, rating, image_url
                FROM products ORDER BY id;
            """)
            product_list = cursor.fetchall() # Fetches as list of dicts
        except Error as e:
            print(f"Error fetching products: {e}")
            flash("Error fetching products from database.", "error")
        finally:
            if conn:
                conn.close()
    else:
        flash("Error connecting to database to fetch products.", "error")

    # current_user is now available via Flask-Login
    user_display = current_user.name if current_user.is_authenticated else None
    return render_template('index.html',
                           products=product_list,
                           user=user_display,
                           is_admin=current_user.is_authenticated and current_user.is_admin)

# --- USER PROFILE ROUTES ---
@app.route('/profile')
@login_required # Protects this route, redirects to login if not authenticated
def profile():
    # current_user is provided by Flask-Login
    user_email = current_user.email
    user_id = current_user.id

    user_details = {
        'name': current_user.name,
        'email': user_email,
        'address': 'Not provided',
        'phone': 'Not provided'
    }
    user_orders = [] # Initialize as empty list

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor

            # Fetch user details
            cursor.execute("SELECT name, email, address, phone FROM users WHERE id = %s",
                        (user_id,)) # Fetch by ID for consistency with load_user
            rec = cursor.fetchone()
            if rec:
                user_details['name'] = rec['name']
                user_details['email'] = rec['email']
                user_details['address'] = rec['address'] or 'Not provided'
                user_details['phone'] = rec['phone'] or 'Not provided'

            # Fetch user orders using a single query with JSON aggregation for items
            cursor.execute("""
                SELECT
                    o.id,
                    o.razorpay_order_id,
                    o.total_amount,
                    o.status,
                    o.order_date,
                    json_agg(json_build_object(
                        'product_id', oi.product_id,
                        'product_name', oi.product_name,
                        'quantity', oi.quantity,
                        'price_at_purchase', oi.price_at_purchase,
                        'image_url', oi.image_url
                    )) AS items
                FROM
                    orders o
                JOIN
                    order_items oi ON o.id = oi.order_id
                WHERE
                    o.user_id = %s -- Use user_id from Flask-Login
                GROUP BY
                    o.id, o.razorpay_order_id, o.total_amount, o.status, o.order_date
                ORDER BY
                    o.order_date DESC;
            """, (user_id,)) # Pass user_id
            orders_data = cursor.fetchall()

            for order_row in orders_data:
                # Format date directly from the RealDictCursor result
                order_row['order_date'] = order_row['order_date'].strftime('%Y-%m-%d %H:%M:%S')
                user_orders.append(order_row) # Append the dict directly

        except Exception as e:
            print(f"Error fetching profile data or orders: {e}")
            flash("Error loading profile data or orders.", "error")
        finally:
            if conn:
                conn.close()

    return render_template('profile.html',
                           user=user_details['name'],
                           user_details=user_details,
                           user_orders=user_orders)

@app.route('/update_profile', methods=['POST'])
@login_required # Protect this route
def update_profile():
    # current_user is available
    user_id = current_user.id

    name = request.form.get('name')
    email = request.form.get('email') # Should handle if email changes and is unique
    address = request.form.get('address')
    phone = request.form.get('phone')

    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('profile'))

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
               SET name = %s, email = %s, address = %s, phone = %s
             WHERE id = %s -- Update by ID, not email
        """, (name, email, address, phone, user_id))
        conn.commit()

        # Update current_user object and session for immediate reflection
        current_user.name = name
        current_user.email = email
        flash("Profile updated successfully!", "success")
    except Error as e:
        print(f"Error updating profile: {e}")
        flash("Failed to update profile.", "error")
    finally:
        if conn:
            cur.close()
            conn.close()
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required # Protect this route
def change_password():
    # current_user is available
    user_id = current_user.id

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "error")
        return redirect(url_for('profile', _anchor='password-change')) # Redirect to correct tab

    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('profile'))

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor
        cur.execute("SELECT password FROM users WHERE id = %s", (user_id,)) # Fetch by ID
        rec = cur.fetchone()

        if rec and rec['password'] == current_password:  # NOTE: Use password hashing (e.g., bcrypt) in production!
            cur.execute("UPDATE users SET password = %s WHERE id = %s",
                        (new_password, user_id))
            conn.commit()
            flash("Password changed successfully! You will be logged out for security.", "success")
            logout_user() # Log out after password change for security
            return redirect(url_for('login'))
        else:
            flash("Incorrect current password.", "error")
    except Error as e:
        print(f"Error changing password: {e}")
        flash("Failed to change password.", "error")
    finally:
        if conn:
            cur.close()
            conn.close()
    return redirect(url_for('profile', _anchor='password-change'))


# --- PRODUCT & CART ROUTES ---
@app.route('/add_product', methods=['GET', 'POST'])
@login_required # Only logged-in users can add products
def add_product():
    if not current_user.is_admin: # Check admin status from current_user
        if request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': 'Admins only.'}), 403
        flash("Unauthorized. Admins only.", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            name = request.form['name']
            category = request.form['category']
            rating = float(request.form['rating'])
            price = float(request.form['price'])
            description = request.form['description']
            image_file = request.files.get('image')
            image_url = None

            if image_file and image_file.filename:
                filename = secure_filename(image_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                image_url = f'img/Products/{filename}'

            conn = connect_to_db()
            if not conn:
                return jsonify({'success': False, 'message': 'DB connection failed.'}), 500
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (name, category, rating, price, description, image_url, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, category, rating, price, description, image_url, current_user.email)) # Use current_user.email
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Product added successfully!'})
        except Exception as e:
            print(f"Add product error: {e}")
            return jsonify({'success': False, 'message': 'Error adding product.'}), 500

    return render_template('add_product.html')

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required # Only logged-in users can edit products
def edit_product(product_id):
    if not current_user.is_admin:
        flash("Unauthorized. Admins only.", "warning")
        return redirect(url_for('index'))

    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.")
        return redirect(url_for('index'))
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']
        rating = request.form['rating']
        image_file = request.files.get('image')
        image_url = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = f'img/Products/{filename}'
        try:
            if image_url:
                cur.execute("""
                    UPDATE products
                       SET name=%s, description=%s, category=%s, price=%s, rating=%s, image_url=%s
                     WHERE id=%s
                """, (name, description, category, price, rating, image_url, product_id))
            else:
                cur.execute("""
                    UPDATE products
                       SET name=%s, description=%s, category=%s, price=%s, rating=%s
                     WHERE id=%s
                """, (name, description, category, price, rating, product_id))
            conn.commit()
            flash("Product updated!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Update product error: {e}")
            flash("Error updating product.", "error")
            return redirect(url_for('index'))
        finally:
            if conn:
                cur.close()
                conn.close()

    try:
        cur.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone() # Fetch as dict
        if not product:
            flash("Product not found.", "warning")
            return redirect(url_for('index'))
        return render_template('edit_product.html', product=product)
    except Exception as e:
        print(f"Fetch product error: {e}")
        flash("Error fetching product.", "error")
        return redirect(url_for('index'))
    finally:
        if conn:
            cur.close()
            conn.close()

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required # Only logged-in users can delete products
def delete_product(product_id):
    if not current_user.is_admin:
        flash("Unauthorized. Admins only.", "warning")
        return redirect(url_for('index'))

    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            flash("Product deleted!", "success")
        except Error as e:
            print(f"Delete product error: {e}")
            flash("Error deleting product.", "error")
        finally:
            if conn:
                conn.close()
        return redirect(url_for('index'))
    flash("Database connection failed.", "error")
    return "Database connection failed", 500

@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))

    product, reviews, user_review = None, [], None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor
        cur.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s",
                    (product_id,))
        product = cur.fetchone() # Fetch as dict
        if not product:
            flash("Product not found.", "warning")
            return redirect(url_for('index'))

        if request.method == 'POST':
            if not current_user.is_authenticated: # Check Flask-Login authentication
                flash("Please log in to submit a review.", "warning")
                return redirect(url_for('login'))

            # Current user's ID from Flask-Login
            user_id = current_user.id
            user_name = current_user.name # Or fetch from DB if more detailed name is needed

            rating = request.form.get('rating', type=int)
            comment = request.form.get('comment')

            if not rating or not comment:
                flash("Provide both a rating and a comment.", "error")
            elif rating < 1 or rating > 5:
                flash("Rating must be between 1 and 5.", "error")
            else:
                cur.execute("SELECT id FROM reviews WHERE product_id = %s AND user_id = %s",
                            (product_id, user_id))
                existing = cur.fetchone()
                if existing:
                    cur.execute("""
                        UPDATE reviews
                           SET rating=%s, comment=%s, created_at=CURRENT_TIMESTAMP
                         WHERE id=%s
                    """, (rating, comment, existing['id'])) # Access 'id' from dict
                    flash("Your review has been updated!", "success")
                else:
                    cur.execute("""
                        INSERT INTO reviews (product_id, user_id, username, rating, comment)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (product_id, user_id, user_name, rating, comment))
                    flash("Thanks for your review!", "success")
                conn.commit()
                return redirect(url_for('product_detail', product_id=product_id))

        cur.execute("""
            SELECT username, rating, comment, created_at
              FROM reviews
             WHERE product_id = %s
          ORDER BY created_at DESC
        """, (product_id,))
        reviews_data = cur.fetchall() # Fetches as list of dicts
        for r in reviews_data:
            r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M') # Format date
            reviews.append(r)

        if current_user.is_authenticated: # Check Flask-Login authentication
            cur.execute("""
                SELECT r.rating, r.comment
                  FROM reviews r
                  JOIN users u ON u.id = r.user_id
                 WHERE r.product_id = %s AND u.id = %s -- Use user_id
            """, (product_id, current_user.id))
            ur = cur.fetchone()
            if ur:
                user_review = {'rating': ur['rating'], 'comment': ur['comment']} # Access as dict

    except Error as e:
        print(f"product_detail error: {e}")
        flash("Error loading product details.", "error")
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

    return render_template('product_detail.html', product=product, reviews=reviews, user_review=user_review)


@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
@login_required # Requires login to add to cart
def add_to_cart(product_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor
            cursor.execute(
                "SELECT name, price, image_url FROM products WHERE id = %s",
                (product_id,)
            )
            product = cursor.fetchone() # Fetch as dict
            if product:
                # Store product details in cart session (Python dict)
                if 'cart' not in session:
                    session['cart'] = []
                found = False
                for item in session['cart']:
                    if item['id'] == product_id:
                        item['quantity'] += 1
                        found = True
                        break
                if not found:
                    session['cart'].append({
                        'id': product_id,
                        'name': product['name'],
                        'price': float(product['price']), # Ensure price is float
                        'quantity': 1,
                        'image_url': product['image_url']
                    })
                session.modified = True
                flash(f"{product['name']} added to cart!", "success")
            else:
                flash("Product not found.", "error")
        except Error as e:
            print(f"Error adding to cart: {e}")
            flash("Error adding product to cart.", "error")
        finally:
            if conn:
                conn.close()
    else:
        flash("Database connection failed, cannot add to cart.", "error")
    return redirect(request.referrer or url_for('index')) # Redirect back to where they came from

@app.route('/remove_from_cart/<int:product_id>', methods=['GET', 'POST'])
@login_required # Requires login to modify cart
def remove_from_cart(product_id):
    if 'cart' in session:
        original_cart_length = len(session['cart'])
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        new_cart_length = len(session['cart'])

        if new_cart_length < original_cart_length:
            session.modified = True
            flash("Item removed from cart.", "info")
        else:
            flash("Item not found in your cart.", "warning")
            session.modified = True # Good practice to mark as modified even if no change

    else:
        flash("Your cart is already empty.", "info")

    return redirect(url_for('cart'))

@app.route('/update_quantity/<int:product_id>/<string:action>', methods=['POST'])
@login_required # Requires login to update quantity
def update_quantity(product_id, action):
    if 'cart' not in session:
        session['cart'] = [] # Initialize if somehow not present
    item_found = False
    for item in session['cart']:
        if item['id'] == product_id:
            item_found = True
            if action == 'increase':
                item['quantity'] += 1
                flash(f"Quantity for {item['name']} increased.", "success")
            elif action == 'decrease':
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                    flash(f"Quantity for {item['name']} decreased.", "info")
                else:
                    # If quantity is 1 and user clicks decrease, remove the item
                    session['cart'] = [i for i in session['cart'] if i['id'] != product_id]
                    flash(f"{item['name']} removed from cart.", "info")
            session.modified = True
            break
    if not item_found:
        flash("Product not found in cart.", "error")
    return redirect(url_for('cart'))


@app.route('/cart')
@login_required # Cart requires login
def cart():
    cart_items = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    razorpay_order_id = None
    if total_price > 0:
        try:
            order_data = {
                "amount": int(total_price * 100),  # Razorpay expects amount in paise (integer)
                "currency": "INR",
                "payment_capture": 1
            }
            order = razorpay_client.order.create(order_data)
            razorpay_order_id = order['id']
        except Exception as e:
            print(f"Error creating Razorpay order: {e}")
            flash("Error processing payment. Please try again.", "error")

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_price=total_price,
        razorpay_order_id=razorpay_order_id,
        razorpay_key=RAZORPAY_KEY_ID # Use the key from config
    )

@app.context_processor
def inject_cart_count():
    cart_items = session.get('cart', [])
    total_quantity = sum(item['quantity'] for item in cart_items)
    return dict(cart_count=total_quantity)

@app.route('/payment/success', methods=['POST'])
@login_required # Payment success route should be protected
def payment_success():
    conn = None
    try:
        # Request data will come as form data from Razorpay's direct form submission
        payment_id = request.form.get('razorpay_payment_id')
        order_id_from_razorpay = request.form.get('razorpay_order_id')
        signature = request.form.get('razorpay_signature')

        # Verify the payment signature
        params_dict = {
            'razorpay_order_id': order_id_from_razorpay,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        # Payment is verified, proceed to save order details
        user_id = current_user.id # Get user ID from Flask-Login
        user_email = current_user.email # Get user email from Flask-Login
        cart_items = session.get('cart', [])
        total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

        conn = connect_to_db()
        cursor = conn.cursor()

        # Insert into orders table
        cursor.execute(
            """
            INSERT INTO orders (user_id, user_email, razorpay_order_id, razorpay_payment_id, total_amount, status, order_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """,
            (user_id, user_email, order_id_from_razorpay, payment_id, total_amount, 'Completed', datetime.now())
        )
        new_order_db_id = cursor.fetchone()[0]

        # Insert into order_items table for each product in the cart
        for item in cart_items:
            cursor.execute(
                """
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price_at_purchase, image_url)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (new_order_db_id, item['id'], item['name'], item['quantity'], item['price'], item['image_url'])
            )
        conn.commit()

        # Clear the user's cart from the session
        session.pop('cart', None)
        session.modified = True

        flash("Payment successful! Your order has been placed and confirmed.", "success")
        return redirect(url_for('thankyou')) # Redirect to the thankyou page

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Payment processing failed: {e}. Please try again or contact support.", "error")
        print(f"Razorpay Payment Success Route Error: {e}")
        return redirect(url_for('cart')) # Redirect back to cart with an error message
    finally:
        if conn:
            conn.close()

@app.route('/thankyou')
def thankyou():
    """
    Renders the thank you page after a successful payment.
    """
    return render_template('thankyou.html')

# --- SITEMAP (for local testing, typically served by web server in prod) ---
@app.route('/sitemap.xml')
def serve_sitemap():
    if app.debug or os.environ.get('FLASK_ENV') == 'development':
        return send_from_directory(app.root_path, 'sitemap.xml')
    else:
        return redirect(url_for('static', filename='sitemap.xml'), code=301)


# --- APPLICATION BOOTSTRAP ---
if __name__ == '__main__':
    conn = connect_to_db()
    if conn:
        print("Database connection successful. Creating tables if they don't exist...")
        create_users_table(conn)
        create_products_table(conn)
        create_reviews_table(conn)
        create_orders_table(conn) # Create orders table
        create_order_items_table(conn) # Create order_items table
        conn.close()
        print("Tables checked/created. Starting Flask app.")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("Failed to connect to the database. Exiting.")
