import os
import psycopg2
from psycopg2 import Error
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.secret_key = 'supersecretkey'  # Needed for flash messages

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

@app.route('/')
def index():
    conn = connect_to_db()
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
            return render_template('index.html', products=product_list)
        except Error as e:
            print(f"Error fetching products: {e}")
            return "Error fetching products", 500
        finally:
            conn.close()
    return "Error connecting to database", 500

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        rating = request.form['rating']
        description = request.form['description']
        image = request.files['image']

        image_url = ''
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = f'img/Products/{filename}'

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO products (name, description, category, price, rating, image_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, description, category, price, rating, image_url))
                conn.commit()
                flash("Product added successfully!")
                return redirect(url_for('index'))
            except Error as e:
                print(f"Error inserting product: {e}")
                return "Error inserting product", 500
            finally:
                conn.close()
        return "Database connection failed", 500
    return render_template('add_product.html')

if __name__ == '__main__':
    conn = connect_to_db()
    if conn:
        create_products_table(conn)
        conn.close()
    app.run(host='0.0.0.0', port=5000, debug=True)
