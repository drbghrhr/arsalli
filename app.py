from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from datetime import datetime
import secrets

app = Flask(__name__)

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('send_to_me.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            phone TEXT UNIQUE,
            username TEXT UNIQUE,
            otp TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT,
            timestamp TEXT,
            sender_alias TEXT,
            recipient_phone TEXT,
            recipient_username TEXT
        )
    ''')
    conn.commit()
    conn.close()

# الصفحة الرئيسية
@app.route('/')
def home():
    return redirect(url_for('register'))

# تسجيل المستخدم
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        username = request.form.get('username')
        otp = secrets.token_hex(3)  # OTP عشوائي
        
        conn = sqlite3.connect('send_to_me.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (phone, username, otp) VALUES (?, ?, ?)', 
                          (phone, username, otp))
            conn.commit()
            
            # محاكاة إرسال OTP (استبدل هذا بـ Twilio API في الإنتاج)
            print(f"📱 تم إرسال OTP إلى {phone}: {otp}")
            
            return f'''
                <h2>تم التسجيل!</h2>
                <p>تحقق من OTP في الواتساب/رسالة SMS.</p>
                <a href="{url_for('inbox', phone=phone, otp=otp)}">الدخول إلى صندوق الوارد</a>
            '''
        except sqlite3.IntegrityError:
            return "رقم الجوال أو اسم المستخدم مسجل مسبقاً!", 400
        finally:
            conn.close()
    
    return render_template('register.html')

# إرسال رسالة مجهولة
@app.route('/send/<recipient_identifier>', methods=['GET', 'POST'])
def send_message(recipient_identifier):
    if request.method == 'POST':
        content = request.form['message']
        alias = request.form.get('alias', 'مجهول')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect('send_to_me.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT phone, username FROM users WHERE phone=? OR username=?', 
                      (recipient_identifier, recipient_identifier))
        user = cursor.fetchone()
        
        if user:
            phone, username = user
            cursor.execute('''
                INSERT INTO messages (content, timestamp, sender_alias, recipient_phone, recipient_username)
                VALUES (?, ?, ?, ?, ?)
            ''', (content, timestamp, alias, phone, username))
            conn.commit()
            conn.close()
            return "تم إرسال رسالتك بنجاح! ✅"
        else:
            conn.close()
            return "المستقبِل غير موجود! ❌", 404
    
    return render_template('send.html', recipient=recipient_identifier)

# صندوق الوارد
@app.route('/inbox')
def inbox():
    phone = request.args.get('phone')
    otp = request.args.get('otp')
    
    if not phone or not otp:
        return "مطلوب رقم الجوال وOTP للدخول!", 403
    
    conn = sqlite3.connect('send_to_me.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE phone=? AND otp=?', (phone, otp))
    if not cursor.fetchone():
        conn.close()
        return "OTP غير صحيح! 🔒", 403
    
    cursor.execute('''
        SELECT * FROM messages 
        WHERE recipient_phone=? OR recipient_username=?
        ORDER BY timestamp DESC
    ''', (phone, phone))
    messages = cursor.fetchall()
    conn.close()
    
    return render_template('inbox.html', messages=messages)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)