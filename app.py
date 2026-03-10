from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import random

app = Flask(__name__)
app.secret_key = 'chakravyuh_2026_artisan_secret'

# Database Configuration
db_config = {
    'host': "localhost",
    'user': "root",
    'password': "root",
    'database': "artisan_marketplace"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- HOME / MARKETPLACE ---
@app.route('/')
def home():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    all_products = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("index.html", products=all_products)

# --- AUTHENTICATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            db.commit()
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            session.update({'loggedin': True, 'user_id': user[0], 'name': name})
            return redirect(url_for('dashboard'))
        except mysql.connector.Error as err:
            return f"Error: {err}"
        finally:
            cursor.close()
            db.close()
    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        if user:
            session.update({'loggedin': True, 'user_id': user['id'], 'name': user['name']})
            return redirect(url_for('dashboard'))
    return render_template("login.html")

# --- ARTISAN DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE artisan_id = %s", (session['user_id'],))
        my_products = cursor.fetchall()
        cursor.execute("""
            SELECT orders.*, products.title AS product_name 
            FROM orders 
            JOIN products ON orders.product_id = products.id 
            WHERE orders.artisan_id = %s ORDER BY orders.id DESC
        """, (session['user_id'],))
        my_orders = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template("dashboard.html", name=session['name'], products=my_products, orders=my_orders)
    return redirect(url_for('login'))

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'loggedin' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        price = request.form['price']
        category = request.form['category']
        image_url = request.form['image_url']
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("INSERT INTO products (title, price, category, image_url, artisan_id) VALUES (%s, %s, %s, %s, %s)", 
                       (title, price, category, image_url, session['user_id']))
        db.commit()
        cursor.close()
        db.close()
        return redirect(url_for('dashboard'))
    return render_template("add_product.html")

# --- PRODUCT REMOVAL ---
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'loggedin' in session:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("DELETE FROM products WHERE id = %s AND artisan_id = %s", (product_id, session['user_id']))
        db.commit()
        cursor.close()
        db.close()
    return redirect(url_for('dashboard'))

# --- BUYING & PAYMENT ---
@app.route('/payment_selection/<int:product_id>')
def payment_selection(product_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template("payment_selection.html", product=product)

@app.route('/buy/<int:product_id>', methods=['POST'])
def buy_product(product_id):
    payment_method = request.form.get('payment_method', 'COD')
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, artisan_id, title FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if product:
        status = f"Packing ({payment_method})"
        cursor.execute("INSERT INTO orders (product_id, artisan_id, customer_name, status) VALUES (%s, %s, %s, %s)", 
                       (product_id, product['artisan_id'], "Guest Buyer", status))
        db.commit()
        tx_id = f"TXN{random.randint(100000, 999999)}"
        cursor.close()
        db.close()
        return render_template("order_success.html", product=product, tx_id=tx_id, method=payment_method)
    db.close()
    return redirect(url_for('home'))

@app.route('/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    new_status = request.form.get('new_status')
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)