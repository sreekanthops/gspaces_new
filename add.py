from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']
        rating = request.form['rating']
        image = request.files['image']

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)

            conn = get_db_connection()
            conn.execute(
                'INSERT INTO products (name, description, category, price, rating, image_url) VALUES (%s, %s, %s, %s, %s, %s)',
                (name, description, category, price, rating, image_path)
            )
            conn.commit()
            conn.close()

            flash('Product added successfully!')
            return redirect(url_for('add_product'))
        else:
            flash('Invalid image format. Allowed: png, jpg, jpeg, webp.')

    return render_template('add_product.html')
