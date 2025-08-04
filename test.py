import psycopg2
from psycopg2 import Error
from flask import Flask, render_template, url_for

app = Flask(__name__, static_folder='static')

# Database configuration
DB_NAME = "gspaces"
DB_USER = "sri"
DB_PASSWORD = "gspaces2025"
DB_HOST = "localhost"
DB_PORT = "5432"

def connect_to_db():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Connection to PostgreSQL DB successful")
        return conn
    except Error as e:
        print(f"Error connecting to PostgreSQL DB: {e}")
        return None

def create_products_table(conn):
    """Creates the 'products' table if it doesn't exist."""
    try:
        cursor = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            price DECIMAL(10, 2),
            image_url VARCHAR(255)
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'products' created successfully or already exists.")
    except Error as e:
        print(f"Error creating table 'products': {e}")

def insert_sample_products(conn):
    """Inserts sample product data if the table is empty."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products;")
        if cursor.fetchone()[0] == 0:
            insert_query = """
            INSERT INTO products (name, description, category, price, image_url) VALUES
            ('The Ergonomic Elite', 'Designed for comfort and posture support to enhance long-term productivity.', 'Ergonomic', 85000.00, 'img/Products/app-1.jpg'),
            ('The Modern Minimalist', 'Features a sleek design with essential elements for a clean, distraction-free workspace.', 'Minimalist', 60000.00, 'img/Products/app-2.jpg'),
            ('The Executive Command', 'A luxurious and robust design, ideal for high-level professionals.', 'Executive', 90000.00, 'img/Products/app-3.jpg'),
            ('The Productivity Pro', 'A comprehensive package including a desk, chair, and essential accessories for optimal performance.', 'Performance', 75000.00, 'img/Products/app-4.jpg'),
            ('The Creative Corner', 'Optimized for creative professionals, offering ample space and smart storage solutions.', 'Creative', 68000.00, 'img/Products/app-5.jpg'),
            ('The Home Office Hub', 'Provides everything needed for a comfortable and efficient home office setup.', 'Home Office', 55000.00, 'img/Products/app-6.jpg');
            """
            cursor.execute(insert_query)
            conn.commit()
            print("Sample data inserted successfully into 'products'.")
        else:
            print("Table 'products' already contains data. Skipping sample data insertion.")
    except Error as e:
        print(f"Error inserting sample data into 'products': {e}")

@app.route('/')
def index():
    """Renders the landing page with product list."""
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, category, price, image_url FROM products ORDER BY id;")
            products_data = cursor.fetchall()

            products_list = []
            for p_id, name, description, category, price, image_url in products_data:
                products_list.append({
                    'id': p_id,
                    'name': name,
                    'description': description,
                    'category': category,
                    'price': float(price),
                    'image_url': image_url
                })

            return render_template('index.html', products=products_list)
        except Error as e:
            print(f"Error fetching products: {e}")
            return "Error fetching products", 500
        finally:
            conn.close()
    return "Error connecting to database", 500

if __name__ == "__main__":
    connection = connect_to_db()
    if connection:
        create_products_table(connection)
        insert_sample_products(connection)
        connection.close()
    app.run(host="0.0.0.0", port=5000, debug=True)

