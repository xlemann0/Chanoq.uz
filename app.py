import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)
app.secret_key = 'chanoq_secret_key_2026'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

def init_db():
    conn = sqlite3.connect('chanoq.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            price TEXT NOT NULL,
            details TEXT NOT NULL,
            phone TEXT NOT NULL,
            telegram TEXT NOT NULL,
            image TEXT NOT NULL,
            receipt TEXT NOT NULL,
            status TEXT DEFAULT 'Kutilmoqda',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    category = request.args.get('category', '')
    region = request.args.get('region', '')
    search = request.args.get('search', '')

    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM ads WHERE status = 'Tasdiqlangan'"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if region:
        query += " AND region = ?"
        params.append(region)
    if search:
        query += " AND (title LIKE ? OR details LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    cursor.execute(query, params)
    ads = cursor.fetchall()
    conn.close()

    return render_template('index.html', ads=ads, category=category, region=region, search=search)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'Dilshod' and password == 'Dilshod2026':
            session['admin'] = True
            flash("Admin panelga xush kelibsiz!", "success")
            return redirect(url_for('admin_panel'))

        conn = sqlite3.connect('chanoq.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Muvaffaqiyatli kirdingiz!", "success")
            return redirect(url_for('index'))
        else:
            flash("Login yoki parol xato!", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect('chanoq.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            flash("Ro'yxatdan o'tdingiz, endi kiring!", "success")
            return redirect(url_for('login'))
        except:
            flash("Bu foydalanuvchi nomiband band!", "danger")
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Tizimdan chiqildi.", "info")
    return redirect(url_for('index'))

@app.route('/add-ad', methods=['GET', 'POST'])
def add_ad():
    if 'user_id' not in session:
        flash("E'lon berish uchun avval ro'yxatdan o'ting yoki kiring!", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        region = request.form['region']
        price = request.form['price']
        details = request.form['details']
        phone = request.form['phone']
        telegram = request.form['telegram']

        image_file = request.files['image']
        receipt_file = request.files['receipt']

        if image_file and receipt_file:
            img_name = secure_filename(image_file.filename)
            rec_name = secure_filename(receipt_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
            receipt_file.save(os.path.join(app.config['UPLOAD_FOLDER'], rec_name))

            conn = sqlite3.connect('chanoq.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ads (user_id, title, category, region, price, details, phone, telegram, image, receipt, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Kutilmoqda')
            ''', (session['user_id'], title, category, region, price, details, phone, telegram, img_name, rec_name))
            conn.commit()
            conn.close()

            flash("E'loningiz adminga yuborildi! Tekshirilgach saytga chiqariladi.", "success")
            return redirect(url_for('index'))

    return render_template('add_ad.html')

@app.route('/my-ads')
def my_ads():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ads WHERE user_id = ?", (session['user_id'],))
    ads = cursor.fetchall()
    conn.close()
    return render_template('my_ads.html', ads=ads)

@app.route('/delete-ad/<int:id>')
def delete_ad(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('chanoq.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ads WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    flash("E'lon o'chirildi.", "info")
    return redirect(url_for('my_ads'))

@app.route('/admin-panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ads")
    ads = cursor.fetchall()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin_panel.html', ads=ads, users=users)

@app.route('/admin/approve/<int:id>')
def admin_approve(id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('chanoq.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE ads SET status = 'Tasdiqlangan' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<int:id>')
def admin_reject(id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('chanoq.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE ads SET status = 'Rad etilgan' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)
