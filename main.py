import os
import random
import string
import psycopg2
from psycopg2 import Error
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from werkzeug.utils import secure_filename

# Google One Tap (ID token verification)
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

# Google OAuth (redirect flow)
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import razorpay
from flask import Flask
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, send_from_directory, redirect, url_for

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=("rzp_test_R8kjO6mYzobvGe", "GEyMn1xy9x8rLlBaKP7473lb"))

app = Flask(__name__) 

# Mail Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sri.chityala501@gmail.com'
app.config['MAIL_PASSWORD'] = 'zupd zixc vvzp kptk'
app.config['MAIL_DEFAULT_SENDER'] = 'sri.chityala501@gmail.com'

mail = Mail(app)

# Serializer for password reset
app.secret_key = 'supersecretkey'
s = URLSafeTimedSerializer(app.secret_key)
# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
# Read from env if available; fallback to the values you pasted.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "226581903418-3ed1eqsl14qlou4nmk2m9sdf6il1mluu.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")

ADMIN_EMAILS = {"sri.chityala501@gmail.com", "srichityala501@gmail.com"}

DB_NAME = "gspaces"
DB_USER = "sri"
DB_PASSWORD = "gspaces2025"
DB_HOST = "localhost"
DB_PORT = "5432"

# Uploads
UPLOAD_FOLDER = os.path.join('static', 'img', 'Products')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------------------------------------------------------------------
# OAUTH (redirect flow) – optional in addition to One Tap
# -------------------------------------------------------------------
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id="226581903418-3ed1eqsl14qlou4nmk2m9sdf6il1mluu.apps.googleusercontent.com",
    client_secret="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",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# -------------------------------------------------------------------
# DB helpers
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# Utility
# -------------------------------------------------------------------
@app.template_filter('inr')
def inr_format(value):
    try:
        return f"{float(value):.2f}"
    except:
        return value

def upsert_user_from_google(google_sub, name, email):
    """Insert user if missing; return (name, email)."""
    conn = connect_to_db()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name or email.split("@")[0], email, ""))
            conn.commit()
        return (name or email.split("@")[0], email)
    except Exception as e:
        print(f"upsert_user_from_google error: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------------
# Routes: marketing & legal
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# Auth: Email/password login
# -------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = connect_to_db()
        if not conn:
            flash("Database connection failed during login.", "error")
            return render_template('login.html')
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, name, email, password FROM users WHERE email = %s AND password = %s",
                        (email, password))
            user = cur.fetchone()
            if user:
                session.clear()
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['user_email'] = user[2]
                session['is_admin'] = user[2] in ADMIN_EMAILS
                flash(f"Welcome, {session['user_name']}!", "success")
                return redirect(url_for('index'))
            else:
                flash("Invalid email or password", "error")
                return render_template('login.html')
        except Error as e:
            print(f"Login DB error: {e}")
            flash("An error occurred during login.", "error")
            return render_template('login.html')
        finally:
            cur.close()
            conn.close()
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            conn = connect_to_db()
            if not conn:
                flash("Database connection failed.", "error")
                return redirect(url_for('signup'))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered.", "error")
                return render_template('login.html')
            
            cursor.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """, (name, email, password))
            conn.commit()
            flash("Signup successful. Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            print(f"❌ Signup error: {e}")
            flash("Signup failed due to a server error.", "error")
            return render_template('login.html')
        finally:
            if conn:
                cursor.close()
                conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Ensure all relevant session keys are popped
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('is_admin', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# -------------------------------------------------------------------
# Google OAuth (redirect flow) — optional button to “Continue with Google”
# -------------------------------------------------------------------
@app.route("/login/google")
def login_google():
    redirect_uri = url_for("auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token)
        email = user_info.get("email")
        name = user_info.get("name") or (email.split("@")[0] if email else "User")
        if not email:
            flash("Google did not return an email.", "danger")
            return redirect(url_for("login"))
        session.clear()
        # You might want to get or create a user_id for the Google-authenticated user here
        # For simplicity, we're just setting email and name
        session["user_email"] = email
        session["user_name"] = name
        session["is_admin"] = email in ADMIN_EMAILS
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("profile"))
    except Exception as e:
        print(f"Google callback error: {e}")
        flash("Google login failed. Please try again.", "danger")
        return redirect(url_for("login"))

# -------------------------------------------------------------------
# Google One Tap endpoint
# -------------------------------------------------------------------
@app.route('/google_signin', methods=['GET', 'POST'])
def google_signin():
    if request.method == "GET":
        redirect_uri = url_for("auth_callback", _external=True)
        return oauth.google.authorize_redirect(redirect_uri)
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
        upsert_user_from_google(idinfo.get('sub'), name, email)
        session.clear()
        # Ensure you set 'user_id' if your application logic relies on it for other operations
        session['user_name'] = name
        session['user_email'] = email
        session['is_admin'] = email in ADMIN_EMAILS
        flash(f"Welcome, {name} (Google)!", "success")
        return jsonify({"success": True, "redirect": url_for('index')})
    except ValueError as e:
        print(f"Google token verify error: {e}")
        return make_response(jsonify({"success": False, "message": "Invalid token"}), 400)
    except Exception as e:
        print(f"google_signin server error: {e}")
        return make_response(jsonify({"success": False, "message": "Server error"}), 500)


# ----------------
# Forgot password
# ----------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # Check if user exists
        conn = psycopg2.connect(database="gspaces", user="sri", password="gspaces2025", host="localhost", port="5432")
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        conn.close()

        if user:
            # Generate token valid for 1 hour
            token = s.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)

            # Send email
            msg = Message('Password Reset Request', recipients=[email])
            msg.body = f'''Hi,

To reset your password, click the link below:
{reset_url}

If you didn’t request this, please ignore.

Regards,
GSpaces Team
'''
            mail.send(msg)

            flash('A reset link has been sent to your email.', 'success')
        else:
            flash('No account found with that email.', 'danger')

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verify token (expires in 1 hour = 3600s)
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['password']

        # Update password in DB
        conn = psycopg2.connect(
            database="gspaces",
            user="sri",
            password="gspaces2025",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
        conn.commit()
        conn.close()

        flash('Your password has been reset. Please login.', 'success')
        return redirect(url_for('login'))

    # Render reset password form
    return render_template('reset_password.html', token=token)

# -------------------------------------------------------------------
# Home
# -------------------------------------------------------------------
@app.route('/')
def index():
    conn = connect_to_db()
    product_list = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, category, price, rating, image_url
                FROM products ORDER BY id;
            """)
            for row in cursor.fetchall():
                product_list.append({
                    'id': row[0], 'name': row[1], 'description': row[2],
                    'category': row[3], 'price': float(row[4]),
                    'rating': float(row[5]) if row[5] is not None else None,
                    'image_url': row[6]
                })
        except Error as e:
            print(f"Error fetching products: {e}")
            flash("Error fetching products from database.", "error")
        finally:
            conn.close()
    else:
        flash("Error connecting to database to fetch products.", "error")

    user_display = session.get('user_name') or session.get('user_email')
    return render_template('index.html',
                           products=product_list,
                           user=user_display,
                           is_admin=session.get('is_admin', False))

# -------------------------------------------------------------------
# Profile
# -------------------------------------------------------------------
@app.route('/profile')
def profile():
    if not session.get('user_email'):
        flash("Please log in to view your profile.", "info")
        return redirect(url_for('login'))

    user_details = {
        'name': session.get('user_name'),
        'email': session.get('user_email'),
        'address': 'Not provided',
        'phone': 'Not provided'
    }

    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT name, email, address, phone FROM users WHERE email = %s",
                        (session['user_email'],))
            rec = cur.fetchone()
            if rec:
                user_details['name'] = rec[0]
                user_details['email'] = rec[1]
                user_details['address'] = rec[2] or 'Not provided'
                user_details['phone'] = rec[3] or 'Not provided'
        except Error as e:
            print(f"Error fetching profile data: {e}")
            flash("Error loading profile data.", "error")
        finally:
            conn.close()

    return render_template('profile.html', user=user_details['name'],
                           user_details=user_details, user_orders=[])

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if not session.get('user_email'):
        flash("Please log in to update your profile.", "warning")
        return redirect(url_for('login'))

    name = request.form.get('name')
    email = request.form.get('email')
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
             WHERE email = %s
        """, (name, email, address, phone, session['user_email']))
        conn.commit()

        session['user_name'] = name
        session['user_email'] = email
        flash("Profile updated successfully!", "success")
    except Error as e:
        print(f"Error updating profile: {e}")
        flash("Failed to update profile.", "error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if not session.get('user_email'):
        flash("Please log in to change your password.", "warning")
        return redirect(url_for('login'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "error")
        return redirect(url_for('profile'))

    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('profile'))

    try:
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE email = %s", (session['user_email'],))
        rec = cur.fetchone()
        if rec and rec[0] == current_password:  # NOTE: use hashing in production!
            cur.execute("UPDATE users SET password = %s WHERE email = %s",
                        (new_password, session['user_email']))
            conn.commit()
            flash("Password changed successfully!", "success")
        else:
            flash("Incorrect current password.", "error")
    except Error as e:
        print(f"Error changing password: {e}")
        flash("Failed to change password.", "error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('profile'))

# -------------------------------------------------------------------
# Products & Cart
# -------------------------------------------------------------------
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        if request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': 'Admins only.'}), 403
        flash("Unauthorized. Admins only.", "warning")
        return redirect(url_for('login'))

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
            """, (name, category, rating, price, description, image_url, session.get('user_email', 'unknown')))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Product added successfully!'})
        except Exception as e:
            print(f"Add product error: {e}")
            return jsonify({'success': False, 'message': 'Error adding product.'}), 500

    return render_template('add_product.html')

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not session.get('is_admin'):
        flash("Unauthorized. Admins only.", "warning")
        return redirect(url_for('index'))

    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.")
        return redirect(url_for('index'))
    cur = conn.cursor()

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
            cur.close()
            conn.close()

    try:
        cur.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s", (product_id,))
        row = cur.fetchone()
        if not row:
            flash("Product not found.", "warning")
            return redirect(url_for('index'))
        product = {
            'id': row[0], 'name': row[1], 'description': row[2], 'category': row[3],
            'price': float(row[4]), 'rating': float(row[5]) if row[5] else None, 'image_url': row[6]
        }
        return render_template('edit_product.html', product=product)
    except Exception as e:
        print(f"Fetch product error: {e}")
        flash("Error fetching product.", "error")
        return redirect(url_for('index'))
    finally:
        cur.close()
        conn.close()

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('is_admin'):
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
            conn.close()
        return redirect(url_for('index'))
    flash("Database connection failed.", "error")
    return "Database connection failed", 500

@app.route('/update_quantity/<int:product_id>/<string:action>', methods=['POST'])
def update_quantity(product_id, action):
    if 'user_email' not in session:
        flash("Please log in to manage your cart.", "warning")
        return redirect(url_for('login'))
    if 'cart' not in session:
        session['cart'] = []
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
    # Redirect back to the cart page to show updated quantities
    return redirect(url_for('cart'))

@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for('index'))

    product, reviews, user_review = None, [], None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s",
                    (product_id,))
        row = cur.fetchone()
        if not row:
            flash("Product not found.", "warning")
            return redirect(url_for('index'))
        product = {
            'id': row[0], 'name': row[1], 'description': row[2], 'category': row[3],
            'price': float(row[4]), 'rating': float(row[5]) if row[5] else None, 'image_url': row[6]
        }

        if request.method == 'POST':
            if not session.get('user_email'):
                flash("Please log in to submit a review.", "warning")
                return redirect(url_for('login'))

            cur.execute("SELECT id, name FROM users WHERE email = %s", (session['user_email'],))
            u = cur.fetchone()
            if not u:
                flash("User not found.", "error")
                return redirect(url_for('login'))
            user_id, user_name = u[0], u[1]

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
                    """, (rating, comment, existing[0]))
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
        for r in cur.fetchall():
            reviews.append({
                'username': r[0], 'rating': r[1], 'comment': r[2],
                'created_at': r[3].strftime('%Y-%m-%d %H:%M')
            })

        if session.get('user_email'):
            cur.execute("""
                SELECT r.rating, r.comment
                  FROM reviews r
                  JOIN users u ON u.id = r.user_id
                 WHERE r.product_id = %s AND u.email = %s
            """, (product_id, session['user_email']))
            ur = cur.fetchone()
            if ur:
                user_review = {'rating': ur[0], 'comment': ur[1]}

    except Error as e:
        print(f"product_detail error: {e}")
        flash("Error loading product details.", "error")
        return redirect(url_for('index'))
    finally:
        conn.close()

    return render_template('product_detail.html', product=product, reviews=reviews, user_review=user_review)

# -------------------------------------------------------------------
# Products & Cart
# -------------------------------------------------------------------
@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    if 'user_email' not in session: # <--- CHANGED THIS LINE
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for('login'))
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, price, image_url FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            if product:
                product_name = product[0]
                product_price = float(product[1])
                product_image_url = product[2]
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
                        'name': product_name,
                        'price': product_price,
                        'quantity': 1,
                        'image_url': product_image_url
                    })
                session.modified = True
                flash(f"{product_name} added to cart!", "success")
            else:
                flash("Product not found.", "error")
        except Error as e:
            print(f"Error adding to cart: {e}")
            flash("Error adding product to cart.", "error")
        finally:
            if conn: # Ensure conn is not None before closing
                conn.close()
    else:
        flash("Database connection failed, cannot add to cart.", "error")
    # Redirect back to the page the user came from
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_from_cart/<int:product_id>', methods=['GET', 'POST'])
def remove_from_cart(product_id):
    if 'user_email' not in session: # <--- CHANGED THIS LINE
        flash("Please log in to manage your cart.", "warning")
        return redirect(url_for('login'))

    if 'cart' in session:
        original_cart_length = len(session['cart'])
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        new_cart_length = len(session['cart'])

        if new_cart_length < original_cart_length:
            session.modified = True
            flash("Item removed from cart.", "info")
        else:
            # Item was not found in the cart
            flash("Item not found in your cart.", "warning")
            session.modified = True # Still good practice to mark as modified even if no change, if you want consistency

    else:
        flash("Your cart is already empty.", "info")

    return redirect(url_for('cart'))

@app.route('/cart') 
def cart():
    if 'cart' not in session or not session['cart']:
        return render_template("cart.html", cart_items=[], total_price=0)
    cart_items = session['cart']
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    # ✅ Create Razorpay Order (only if total_price > 0)
    if total_price > 0:
        order_data = {
            "amount": total_price * 100,  # Razorpay expects amount in paise
            "currency": "INR",
            "payment_capture": 1
        }
        order = razorpay_client.order.create(order_data)
        razorpay_order_id = order['id']
    else:
        razorpay_order_id = None
    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_price=total_price,
        razorpay_order_id=razorpay_order_id,
        razorpay_key="rzp_test_R8kjO6mYzobvGe"  # <-- replace with your actual key_id
    )
    
@app.context_processor
def inject_cart_count():
    cart_items = session.get('cart', [])
    total_quantity = sum(item['quantity'] for item in cart_items)
    return dict(cart_count=total_quantity)
    
@app.route('/payment/success', methods=['POST'])
def payment_success():
    data = request.json
    # You should verify signature here with razorpay utility
    # Save transaction details to DB
    return jsonify({"status": "success"})

@app.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    amount = data['amount'] * 100  # in paise
    order = client.order.create({
        'amount': amount,
        'currency': 'INR',
        'payment_capture': 1
    })
    return jsonify(order)

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    try:
        client.utility.verify_payment_signature(data)
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "failed"}), 400

# --- NEW SECTION FOR LOCAL SITEMAP TESTING ---
@app.route('/sitemap.xml')
def serve_sitemap():
    # Only serve the sitemap if in a development/testing environment
    # In production, your web server (Nginx/Apache) should serve this directly.
    # You might want to add a more robust check here, e.g., based on FLASK_ENV
    if app.debug or os.environ.get('FLASK_ENV') == 'development': # Example check
        # Assuming sitemap.xml is in the root directory of your project
        return send_from_directory(app.root_path, 'sitemap.xml')
    else:
        # In production, redirect or return 404 if accessed via Flask
        return redirect(url_for('static', filename='sitemap.xml'), code=301)
        # Or simply:
        # from flask import abort
        # abort(404)
# --- END NEW SECTION ---

# -------------------------------------------------------------------
# Boot
# -------------------------------------------------------------------
if __name__ == '__main__':
    conn = connect_to_db()
    if conn:
        create_users_table(conn)
        create_products_table(conn)
        create_reviews_table(conn)
        app.run(debug=True)
        conn.close()
    app.run(host='0.0.0.0', port=5000, debug=True)
