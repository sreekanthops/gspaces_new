import os
import psycopg2
import random
import string
from psycopg2 import Error
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask import jsonify # Add this import at the top
import razorpay

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=("rzp_live_R6wg6buSedSnTV", "xeBC7q5tEirlDg4y4Tc3JEc3"))

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

def create_users_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """)
        conn.commit()
        print("Table 'users' ready.")
    except Error as e:
        print(f"Error creating users table: {e}")

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
                image_url VARCHAR(255),
                created_by VARCHAR(255)
            );
        """)
        conn.commit()
        print("Table 'products' ready.")
    except Error as e:
        print(f"Error creating products table: {e}")

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # CHANGE THIS LINE: Receive 'username' instead of 'email'
        username = request.form['username'] 
        password = request.form['password']
        conn = connect_to_db()
        if not conn:
            flash("Database connection failed during login.", "error")
            return render_template('login.html', show_login_form=True)

        cur = conn.cursor()
        try:
            # CHANGE THIS QUERY: Authenticate by 'name' (username) and 'password'
            # Assuming your 'users' table has a 'name' column that stores the username
            cur.execute("SELECT name, email, password FROM users WHERE name = %s AND password = %s", (username, password))
            user_record = cur.fetchone()

            if user_record:
                # Store the user's name (username) in the session
                session['user'] = user_record[0]  # user_record[0] is the name
                session['user'] = user_record[1]  # Store the username
                # Admin check based on name (username)
                session['is_admin'] = (user_record[0] == 'sri')

                flash(f"Welcome, {session['user']}!", "success")
                return redirect('/')
            else:
                flash("Invalid username or password", "error")
                return render_template('login.html', show_login_form=True)
        except Error as e:
            print(f"Login database error: {e}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template('login.html', show_login_form=True)
        finally:
            cur.close()
            conn.close()
    return render_template('login.html')

@app.route('/')
def index():
    conn = connect_to_db()
    product_list = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, category, price, rating, image_url FROM products ORDER BY id;")
            products_data = cursor.fetchall()
            for row in products_data:
                product_list.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'price': float(row[4]),
                    'rating': float(row[5]) if row[5] else None,
                    'image_url': row[6]
                })
        except Error as e:
            print(f"Error fetching products: {e}")
            flash("Error fetching products from database.", "error")
        finally:
            conn.close()
    else:
        flash("Error connecting to database to fetch products.", "error")
    # Pass 'user' (which is now the NAME from session) and 'is_admin' to the template
    return render_template('index.html', 
                           products=product_list, 
                           user=session.get('user'), # This will now be the username
                           is_admin=session.get('is_admin', False)) 
@app.route('/signup', methods=['GET', 'POST']) # Added GET method for displaying signup form
def signup():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            conn = connect_to_db()
            if not conn:
                flash("Database connection failed.", "error")
                return redirect(url_for('signup')) # Redirect back to signup page

            cursor = conn.cursor()
            # Check if email already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered.", "error")
                return render_template('login.html') # Render signup template to show error
            
            # Insert into users
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
            return render_template('login.html') # Render signup template to show error
        finally:
            if conn:
                cursor.close()
                conn.close()
    return render_template('login.html') # For GET request to display the signup form

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('is_admin', None) # Also remove is_admin from session
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = connect_to_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            # generate a temporary password
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # update DB
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (temp_password, email))
            conn.commit()

            flash(f"Your temporary password is: {temp_password}", "success")
            flash("Please login with this password and change it in your profile.", "info")
            return redirect(url_for('login'))
        else:
            flash("Email not found in our records.", "danger")

    return render_template('forgot_password.html')

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    # Authorization check using session['is_admin']
    if not session.get('is_admin'):
        flash("Unauthorized access. Only administrators can edit products.", "warning")
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
            flash("Product updated successfully!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            print(f"❌ Update error: {e}")
            flash("Error updating product.", "error")
            return redirect(url_for('index'))
        finally:
            cursor.close()
            conn.close()
    
    # GET request: Fetch product details
    try:
        cursor.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s", (product_id,))
        row = cursor.fetchone()
        if not row:
            flash("Product not found.", "warning")
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
        flash("Error fetching product for editing.", "error")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    # Authorization check using session['is_admin']
    if not session.get('is_admin'):
        flash("Unauthorized access. Only administrators can delete products.", "warning")
        return redirect(url_for('index'))

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            flash("Product deleted successfully!", "success")
        except Error as e:
            print(f"Error deleting product: {e}")
            flash("Error deleting product.", "error")
        finally:
            conn.close()
        return redirect(url_for('index'))
    flash("Database connection failed.", "error")
    return "Database connection failed", 500
# ... (your existing imports and app setup) ...

# Profile route (already exists, but showing context)
@app.route('/profile')
def profile():
    if 'user' in session:
        # You need to fetch user details to pre-fill the form
        conn = connect_to_db()
        user_details = {
            'name': 'Not provided',
            'email': session['user'], # Use the email from session
            'address': 'Not provided',
            'phone': 'Not provided'
        }
        user_orders = [] # Initialize as empty
        if conn:
            try:
                cursor = conn.cursor()
                # Fetch user details (example - you'll need a users table for full details)
                cursor.execute("SELECT name, email FROM users WHERE email = %s", (session['user'],))
                user_record = cursor.fetchone()
                if user_record:
                    user_details['name'] = user_record[0]
                    # Assuming you might have more columns like address, phone in users table
                    # user_details['address'] = user_record[2]
                    # user_details['phone'] = user_record[3]

                # Fetch user orders (example - you'll need orders and order_items tables)
                # This is a placeholder; you'll need to adapt it to your DB schema
                # cursor.execute("SELECT id, order_date, status, total_amount FROM orders WHERE user_email = %s ORDER BY order_date DESC", (session['user'],))
                # orders_data = cursor.fetchall()
                # for order_row in orders_data:
                #     order_id = order_row[0]
                #     order_items = []
                #     cursor.execute("SELECT product_name, quantity, price_at_purchase, image_url FROM order_items WHERE order_id = %s", (order_id,))
                #     items_data = cursor.fetchall()
                #     for item_row in items_data:
                #         order_items.append({
                #             'product_name': item_row[0],
                #             'quantity': item_row[1],
                #             'price_at_purchase': float(item_row[2]),
                #             'image_url': item_row[3]
                #         })
                #     user_orders.append({
                #         'id': order_id,
                #         'order_date': order_row[1].strftime('%Y-%m-%d'), # Format date
                #         'status': order_row[2],
                #         'total_amount': float(order_row[3]),
                #         'items': order_items
                #     })

            except Error as e:
                print(f"Error fetching profile data: {e}")
                flash("Error loading profile data.", "error")
            finally:
                conn.close()

        return render_template('profile.html', user=user_details['name'], user_details=user_details, user_orders=user_orders) # Pass user_details and user_orders
    else:
        flash("Please log in to view your profile.", "info")
        return redirect(url_for('login'))

# NEW ROUTE: For updating personal details
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        flash("Please log in to update your profile.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email') # Assuming email can be updated, make sure it's unique
        address = request.form.get('address')
        phone = request.form.get('phone')

        conn = connect_to_db()
        if not conn:
            flash("Database connection failed.", "error")
            return redirect(url_for('profile'))
        
        cur = conn.cursor()
        try:
            # Update user details in the database
            # IMPORTANT: Adapt this query to your 'users' table schema
            cur.execute("""
                UPDATE users
                SET name = %s, email = %s, address = %s, phone = %s
                WHERE email = %s
            """, (name, email, address, phone, session['user'])) # Update based on current session email
            
            conn.commit()
            
            # If email was updated, update the session as well
            session['user'] = email 
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile'))
        except Error as e:
            print(f"Error updating profile: {e}")
            flash("Failed to update profile.", "error")
            return redirect(url_for('profile'))
        finally:
            cur.close()
            conn.close()

# NEW ROUTE: For changing password
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        flash("Please log in to change your password.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
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
        
        cur = conn.cursor()
        try:
            # First, verify current password (IMPORTANT: You should be hashing passwords!)
            cur.execute("SELECT password FROM users WHERE email = %s", (session['user'],))
            user_record = cur.fetchone()

            if user_record and user_record[0] == current_password: # In real app, use password hashing (e.g., bcrypt)
                cur.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, session['user']))
                conn.commit()
                flash("Password changed successfully!", "success")
            else:
                flash("Incorrect current password.", "error")
            
            return redirect(url_for('profile'))
        except Error as e:
            print(f"Error changing password: {e}")
            flash("Failed to change password.", "error")
            return redirect(url_for('profile'))
        finally:
            cur.close()
            conn.close()

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        if request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': 'Unauthorized access. Only administrators can add products.'}), 403
        else:
            flash("Unauthorized access. Only administrators can add products.", "warning")
            return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            name = request.form['name']
            category = request.form['category']
            rating = request.form['rating']
            price = request.form['price']
            description = request.form['description']
            image_file = request.files.get('image')
            filename = None
            image_url = None
            if image_file and image_file.filename:
                filename = secure_filename(image_file.filename)
                # Define a subdirectory for product images, if desired
                product_image_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                os.makedirs(product_image_dir, exist_ok=True) # Ensure directory exists
                file_path = os.path.join(product_image_dir, filename)
                image_file.save(file_path)
                print(f"DEBUG: Image saved to: {file_path}")
                # Store the relative path from static, or full URL if served differently
                image_url = f'img/Products/{filename}' # Correct relative path for static files
            conn = connect_to_db()
            if not conn:
                return jsonify({'success': False, 'message': 'Database connection failed during product addition.'}), 500
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO products (name, category, rating, price, description, image_url, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (name, category, float(rating), float(price), description, image_url, session.get('user', 'unknown')))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Product added successfully!'})
        except KeyError as e:
            return jsonify({'success': False, 'message': f'Missing form data: {e}. Please ensure all fields are filled.'}), 400
        except ValueError as e:
            return jsonify({'success': False, 'message': f'Error in data format: {e}. Please check price and rating.'}), 400
        except Error as e:
            print(f"❌ Database error during product insertion: {e}")
            return jsonify({'success': False, 'message': f'Database error: Could not add product. {e}'}), 500
    else:
        return render_template('add_product.html')

# In your main.py

@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    conn = connect_to_db()
    product = None
    reviews = []
    user_review = None # To pre-fill if user has already reviewed

    if conn:
        try:
            cursor = conn.cursor()

            # Fetch product details
            cursor.execute("SELECT id, name, description, category, price, rating, image_url FROM products WHERE id = %s", (product_id,))
            row = cursor.fetchone()
            if row:
                product = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'price': float(row[4]),
                    'rating': float(row[5]) if row[5] else None,
                    'image_url': row[6]
                }
            else:
                flash("Product not found.", "warning")
                return redirect(url_for('index'))

            # Handle new review submission (if POST request)
            if request.method == 'POST':
                if 'user' not in session:
                    flash("Please log in to submit a review.", "warning")
                    return redirect(url_for('login'))

                # Assuming you store user's actual ID in session['user_id'] during login/signup
                # For now, let's get the user ID from the database using username
                current_username = session['user']
                cursor.execute("SELECT id FROM users WHERE name = %s", (current_username,))
                user_record = cursor.fetchone()
                current_user_id = user_record[0] if user_record else None

                rating = request.form.get('rating', type=int)
                comment = request.form.get('comment')

                if not rating or not comment:
                    flash("Please provide both a rating and a comment.", "error")
                elif rating < 1 or rating > 5:
                    flash("Rating must be between 1 and 5.", "error")
                else:
                    # Check if user has already reviewed this product
                    cursor.execute("SELECT id FROM reviews WHERE product_id = %s AND user_id = %s", (product_id, current_user_id))
                    existing_review = cursor.fetchone()

                    if existing_review:
                        # Update existing review
                        cursor.execute("UPDATE reviews SET rating = %s, comment = %s, created_at = CURRENT_TIMESTAMP WHERE id = %s",
                                       (rating, comment, existing_review[0]))
                        flash("Your review has been updated!", "success")
                    else:
                        # Insert new review
                        cursor.execute("INSERT INTO reviews (product_id, user_id, username, rating, comment) VALUES (%s, %s, %s, %s, %s)",
                                       (product_id, current_user_id, current_username, rating, comment))
                        flash("Thank you for your review!", "success")
                    conn.commit()
                    # Redirect to GET to prevent form resubmission
                    return redirect(url_for('product_detail', product_id=product_id))

            # Fetch all reviews for the product (after potential new submission)
            cursor.execute("SELECT username, rating, comment, created_at FROM reviews WHERE product_id = %s ORDER BY created_at DESC", (product_id,))
            reviews_data = cursor.fetchall()
            for r in reviews_data:
                reviews.append({
                    'username': r[0],
                    'rating': r[1],
                    'comment': r[2],
                    'created_at': r[3].strftime('%Y-%m-%d %H:%M') # Format datetime
                })

            # Check if current user has already reviewed for pre-filling the form
            if 'user' in session:
                current_username = session['user']
                cursor.execute("SELECT rating, comment FROM reviews WHERE product_id = %s AND username = %s", (product_id, current_username))
                user_review_data = cursor.fetchone()
                if user_review_data:
                    user_review = {'rating': user_review_data[0], 'comment': user_review_data[1]}


        except Error as e:
            print(f"Error fetching product or reviews: {e}")
            flash("Error loading product details.", "error")
            return redirect(url_for('index')) # Redirect to index on error
        finally:
            conn.close()
    else:
        flash("Database connection failed.", "error")
        return redirect(url_for('index')) # Redirect to index on error

    return render_template('product_detail.html', product=product, reviews=reviews, user_review=user_review)

@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    if 'user' not in session:
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for('login'))
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            # Crucially, fetch the image_url here too!
            cursor.execute("SELECT name, price, image_url FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            if product:
                product_name = product[0]
                product_price = float(product[1])
                product_image_url = product[2] # Fetch the image_url
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
                        'image_url': product_image_url # Store image_url in session
                    })
                session.modified = True
                flash(f"{product_name} added to cart!", "success")
            else:
                flash("Product not found.", "error")
        except Error as e:
            print(f"Error adding to cart: {e}")
            flash("Error adding product to cart.", "error")
        finally:
            conn.close()
    else:
        flash("Database connection failed, cannot add to cart.", "error")
    # Redirect directly to the cart page
    return redirect(url_for('cart'))
@app.route('/remove_from_cart/<int:product_id>', methods=['GET', 'POST'])
def remove_from_cart(product_id):
    if 'user' not in session:
        flash("Please log in to manage your cart.", "warning")
        return redirect(url_for('login'))
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        session.modified = True
        flash("Item removed from cart.", "info")
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
        razorpay_key="rzp_live_R6wg6buSedSnTV"  # <-- replace with your actual key_id
    )

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
