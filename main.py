import os
import psycopg2
from psycopg2 import Error
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask import session 
from flask import session, render_template_string
from flask import flash, get_flashed_messages

app = Flask(__name__, static_folder='static')
app.secret_key = 'supersecretkey'  # Needed for flash messages
# Hardcoded user credentials
VALID_USERS = {
    "sreekanth": "gspaces2025"
}

# Upload folder setup
UPLOAD_FOLDER = os.path.join('static', 'img', 'Products')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configuration
DB_NAME = "gspaces"
DB_USER = "sri"
DB_PASSWORD = "gspaces2025"
DB_HOST = "localhost"
DB_PORT = "5432"

@app.template_filter('inr')
def inr_format(value):
    try:
        return f"{float(value):.2f}"
    except:
        return value

    
def connect_to_db():
    try:
        conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Connected to PostgreSQL DB")
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def create_products_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100),
                price DECIMAL(10, 2),
                rating DECIMAL(2, 1),
                image_url VARCHAR(255)
            );
        """)
        conn.commit()
        print("Table 'products' ready.")
    except Error as e:
        print(f"Error creating table: {e}")

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/')
def index():
    conn = connect_to_db()
    user = session.get('user')  # <-- Add this line

    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, category, price, rating, image_url FROM products ORDER BY id;")
            products = cursor.fetchall()
            product_list = []
            for row in products:
                product_list.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'price': float(row[4]),
                    'rating': float(row[5]) if row[5] else None,
                    'image_url': row[6]
                })
            return render_template('index.html', products=product_list, user=session.get('user'))  # Pass user
        except Error as e:
            print(f"Error fetching products: {e}")
            return "Error fetching products", 500
        finally:
            conn.close()
    return "Error connecting to database", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cur.fetchone()

        if user:
            session['user'] = user[1]  # Assuming user[1] is 'name'
            return redirect('/')
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for('login'))
    
    # This part handles GET request - show login form
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        conn = connect_to_db()
        if conn:
            cursor = conn.cursor()
            # Check if email already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered.", "error")
                return redirect(url_for('login'))

            # Insert into users
            cursor.execute("""
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """, (name, email, password))
            conn.commit()
            flash("Signup successful. Please log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Database connection failed.", "error")
            return redirect(url_for('login'))
    except Exception as e:
        print(f"❌ Signup error: {e}")
        flash("Signup failed due to a server error.", "error")
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if session.get('user') != 'sreekanth':
        flash("Unauthorized access.")
        return redirect(url_for('index'))

    conn = connect_to_db()
    if not conn:
        flash("Database connection failed.")
        return redirect(url_for('index'))

    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']
        rating = request.form['rating']

        # Handle image upload
        image_file = request.files.get('image')
        image_url = None

        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = f'img/Products/{filename}'

        try:
            if image_url:
                cursor.execute("""
                    UPDATE products
                    SET name = %s, description = %s, category = %s, price = %s, rating = %s, image_url = %s
                    WHERE id = %s
                """, (name, description, category, price, rating, image_url, product_id))
            else:
                cursor.execute("""
                    UPDATE products
                    SET name = %s, description = %s, category = %s, price = %s, rating = %s
                    WHERE id = %s
                """, (name, description, category, price, rating, product_id))

            conn.commit()
            flash("Product updated successfully!")
            return redirect(url_for('index'))
        except Exception as e:
            print(f"❌ Update error: {e}")
            flash("Error updating product.")
            return redirect(url_for('index'))
        finally:
            cursor.close()
            conn.close()

    # GET request: Fetch product details
    try:
        cursor.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s", (product_id,))
        row = cursor.fetchone()
        if not row:
            flash("Product not found.")
            return redirect(url_for('index'))

        product = {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'category': row[3],
            'price': float(row[4]),
            'rating': float(row[5]) if row[5] else None,
            'image_url': row[6]
        }

        return render_template('edit_product.html', product=product)

    except Exception as e:
        print(f"❌ Fetch error: {e}")
        flash("Error fetching product.")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            flash("Product deleted successfully!")
        except Error as e:
            print(f"Error deleting product: {e}")
            return "Error deleting product", 500
        finally:
            conn.close()
        return redirect(url_for('index'))
    return "Database connection failed", 500
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user' not in session or session['user'] != 'sreekanth':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            name = request.form['name']
            category = request.form['category']
            rating = request.form['rating']
            price = request.form['price']
            description = request.form['description']
            photo = request.files['photo']
            filename = None

            if photo:
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn = connect_to_db()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO products (name, category, rating, price, description, image_url, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (name, category, rating, price, description, filename, session['user']))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error inserting product: {e}", 500

    return render_template('add_product.html')


if __name__ == '__main__':
    conn = connect_to_db()
    if conn:
        create_products_table(conn)
        conn.close()
    app.run(host='0.0.0.0', port=5000, debug=True)
