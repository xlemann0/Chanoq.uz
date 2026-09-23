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

CATEGORIES = {
    "Uy-joy": ["Uy", "Kvartira", "Yer", "Ijara", "Tijorat binolari"],
    "Avtomobil": ["Yengil avtomobil", "Yuk mashinasi", "Moto", "Ehtiyot qismlar", "Avto xizmatlar"],
    "Ish va vakansiyalar": ["Ish qidiraman", "Ishchi kerak", "Masofaviy ish", "Xizmat ko‘rsatish"],
    "Elektronika": ["Telefon", "Kompyuter", "Noutbuk", "Televizor", "Aksessuarlar"],
    "Uy va mebel": ["Mebel", "Maishiy texnika", "Uy jihozlari"],
    "Kiyim-kechak": ["Erkaklar", "Ayollar", "Bolalar", "Oyoq kiyim"],
    "Tovarlar": ["Yangi", "Ishlatilgan", "Shaxsiy savdo"],
    "Xizmatlar": ["Ta’mirlash", "Yetkazib berish", "Usta xizmatlari", "IT xizmatlar", "Boshqa xizmatlar"],
    "Hayvonlar": ["Uy hayvonlari", "Chorva", "Qushlar"],
    "Ta’lim": ["Kurslar", "Repetitor", "O‘quv markazlari"],
    "Hobbi va ko‘ngilochar": ["O‘yinlar", "Sport", "Musiqa", "To‘plamlar"],
    "Boshqa": ["Boshqa"]
}

def init_db():
    conn = sqlite3.connect('chanoq.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            region TEXT NOT NULL,
            price TEXT NOT NULL,
            salary TEXT,
            details TEXT NOT NULL,
            phone TEXT NOT NULL,
            telegram TEXT NOT NULL,
            image TEXT NOT NULL,
            receipt TEXT NOT NULL,
            status TEXT DEFAULT 'Kutilmoqda',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    # Shaxsiy xabarlar va bildirishnomalar uchun
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    ''')
    # Ommaviy guruh chat uchun jadval
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Har bir sahifada qo'ng'iroqcha uchun o'qilmagan xabarlar sonini hisoblab berish
@app.context_processor
def inject_notifications():
    unread_count = 0
    if 'user_id' in session:
        conn = sqlite3.connect('chanoq.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0", (session['user_id'],))
        res = cursor.fetchone()
        if res:
            unread_count = res[0]
        conn.close()
    elif session.get('admin'):
        conn = sqlite3.connect('chanoq.db')
        cursor = conn.cursor()
        # Admin uchun foydalanuvchilardan kelgan va o'qilmagan xabarlar (receiver_id = 0 yoki maxsus admin id)
        cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = 0 AND is_read = 0")
        res = cursor.fetchone()
        if res:
            unread_count = res[0]
        conn.close()
    return dict(unread_messages_count=unread_count)

@app.route('/')
def index():
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
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
    if subcategory:
        query += " AND subcategory = ?"
        params.append(subcategory)
    if region:
        query += " AND region = ?"
        params.append(region)
    if search:
        query += " AND (title LIKE ? OR details LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    cursor.execute(query, params)
    ads = cursor.fetchall()
    conn.close()

    subcategories = CATEGORIES.get(category, []) if category else []

    return render_template('index.html', ads=ads, categories=CATEGORIES, subcategories=subcategories, 
                           selected_cat=category, selected_subcat=subcategory, region=region, search=search)

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
        phone = request.form['phone']
        try:
            conn = sqlite3.connect('chanoq.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, phone) VALUES (?, ?, ?)", (username, password, phone))
            conn.commit()
            conn.close()
            flash("Ro'yxatdan o'tdingiz, endi kiring!", "success")
            return redirect(url_for('login'))
        except:
            flash("Bu foydalanuvchi nomi band yoki xatolik yuz berdi!", "danger")
    return render_template('register.html')

@app.route('/add-ad', methods=['GET', 'POST'])
def add_ad():
    if 'user_id' not in session:
        flash("E'lon berish uchun avval ro'yxatdan o'ting yoki kiring!", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        subcategory = request.form['subcategory']
        region = request.form['region']
        price = request.form['price']
        salary = request.form.get('salary', '')
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
                INSERT INTO ads (user_id, title, category, subcategory, region, price, salary, details, phone, telegram, image, receipt, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Kutilmoqda')
            ''', (session['user_id'], title, category, subcategory, region, price, salary, details, phone, telegram, img_name, rec_name))
            conn.commit()
            conn.close()

            flash("E'loningiz adminga yuborildi! Tekshirilgach saytga chiqariladi.", "success")
            return redirect(url_for('index'))

    return render_template('add_ad.html', categories=CATEGORIES)

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

@app.route('/edit-ad/<int:id>', methods=['GET', 'POST'])
def edit_ad(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ads WHERE id = ? AND user_id = ?", (id, session['user_id']))
    ad = cursor.fetchone()

    if not ad:
        conn.close()
        flash("E'lon topilmadi yoki sizga tegishli emas.", "danger")
        return redirect(url_for('my_ads'))

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        subcategory = request.form['subcategory']
        region = request.form['region']
        price = request.form['price']
        salary = request.form.get('salary', '')
        details = request.form['details']
        phone = request.form['phone']
        telegram = request.form['telegram']

        image_file = request.files.get('image')
        img_name = ad['image']

        if image_file and image_file.filename != '':
            img_name = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))

        cursor.execute('''
            UPDATE ads SET title=?, category=?, subcategory=?, region=?, price=?, salary=?, details=?, phone=?, telegram=?, image=?, status='Kutilmoqda'
            WHERE id = ? AND user_id = ?
        ''', (title, category, subcategory, region, price, salary, details, phone, telegram, img_name, id, session['user_id']))
        conn.commit()
        conn.close()

        flash("E'lon yangilandi va qayta tasdiqlash uchun adminga yuborildi.", "success")
        return redirect(url_for('my_ads'))

    conn.close()
    return render_template('edit_ad.html', ad=ad, categories=CATEGORIES)

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

@app.route('/ad/<int:id>')
def ad_detail(id):
    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ads WHERE id = ?", (id,))
    ad = cursor.fetchone()
    conn.close()
    if not ad:
        flash("E'lon topilmadi.", "danger")
        return redirect(url_for('index'))
    return render_template('ad_detail.html', ad=ad)

# Foydalanuvchi va Admin o'rtasidagi shaxsiy chat
@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if 'user_id' not in session and not session.get('admin'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        message = request.form['message']
        if session.get('admin'):
            # Admin javob yuboryapti (receiver_id ni formdan yoki tanlangan userdan oladi)
            receiver_id = request.form.get('receiver_id')
            cursor.execute("INSERT INTO messages (sender_id, receiver_id, message, is_read) VALUES (0, ?, ?, 0)", (receiver_id, message))
        else:
            # Foydalanuvchi adminga yozyapti (receiver_id = 0)
            cursor.execute("INSERT INTO messages (sender_id, receiver_id, message, is_read) VALUES (?, 0, ?, 0)", (session['user_id'], message))
        conn.commit()
        flash("Xabar yuborildi!", "success")
        if session.get('admin'):
            return redirect(url_for('admin_chats'))
        return redirect(url_for('messages'))

    if session.get('admin'):
        # Admin uchun barcha yozishmalar ro'yxati
        cursor.execute("SELECT DISTINCT users.id, users.username FROM users JOIN messages ON users.id = messages.sender_id OR users.id = messages.receiver_id")
        chat_users = cursor.fetchall()
        conn.close()
        return render_template('admin_chats.html', chat_users=chat_users)
    else:
        # Foydalanuvchi uchun admin bilan xabarlar
        user_id = session['user_id']
        cursor.execute("SELECT * FROM messages WHERE sender_id = ? OR receiver_id = ? ORDER BY timestamp ASC", (user_id, user_id))
        msgs = cursor.fetchall()
        # O'qilgan qilish
        cursor.execute("UPDATE messages SET is_read = 1 WHERE receiver_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return render_template('messages.html', messages=msgs)

# Admin uchun ma'lum bir user bilan chat tafsiloti
@app.route('/admin/chat/<int:user_id>', methods=['GET', 'POST'])
def admin_chat_detail(user_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == 'POST':
        message = request.form['message']
        cursor.execute("INSERT INTO messages (sender_id, receiver_id, message, is_read) VALUES (0, ?, ?, 0)", (user_id, message))
        conn.commit()
        return redirect(url_for('admin_chat_detail', user_id=user_id))
        
    cursor.execute("SELECT * FROM messages WHERE sender_id = ? OR receiver_id = ? ORDER BY timestamp ASC", (user_id, user_id))
    messages = cursor.fetchall()
    
    # Admin kirganda o'qilgan qilish
    cursor.execute("UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = 0", (user_id,))
    conn.commit()
    conn.close()
    return render_template('admin_chat_detail.html', messages=messages, user_id=user_id)

# Ommaviy guruh chat (Global Chat)
@app.route('/group-chat', methods=['GET', 'POST'])
def group_chat():
    if 'user_id' not in session and not session.get('admin'):
        flash("Guruh chatida yozish uchun tizimga kiring!", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect('chanoq.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            # Kim yozganini aniqlash (User yoki Admin)
            u_id = session.get('user_id', 0) # Admin uchun 0 yoki maxsus qiymat
            cursor.execute("INSERT INTO group_messages (user_id, message) VALUES (?, ?)", (u_id, message))
            conn.commit()
            return redirect(url_for('group_chat'))

    # Guruhdagi barcha xabarlarni foydalanuvchi nomlari bilan birga olish
    cursor.execute('''
        SELECT gm.*, COALESCE(u.username, 'Admin') as username 
        FROM group_messages gm 
        LEFT JOIN users u ON gm.user_id = u.id 
        ORDER BY gm.timestamp ASC
    ''')
    messages = cursor.fetchall()
    conn.close()
    return render_template('group_chat.html', messages=messages)

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
