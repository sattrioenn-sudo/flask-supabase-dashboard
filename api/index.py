from flask import Flask, render_template, request, redirect, url_for, session, flash
from modules.auth import login_user, logout_user
import os

# Konfigurasi Flask agar mengenali folder templates dan static dengan benar di Vercel
app = Flask(__name__, 
            template_folder='../templates', 
            static_folder='../static')

# Secret key untuk mengamankan session (diperlukan agar fitur login berfungsi)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key-yang-sangat-rahasia")

@app.route('/')
def index():
    """Halaman utama, jika belum login dilempar ke login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Menangani tampilan login dan proses submit form"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Memanggil fungsi dari modules/auth.py yang kita buat sebelumnya
        user, error = login_user(email, password)
        
        if user:
            # Simpan info penting ke session browser
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('dashboard'))
        else:
            # Jika gagal, tampilkan pesan error di halaman login
            flash(f"Login Gagal: {error}", "danger")
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Halaman dashboard utama (hanya untuk yang sudah login)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    return render_template('dashboard.html', email=session['user_email'])

@app.route('/logout')
def logout():
    """Menghapus session dan logout"""
    session.clear()
    logout_user()
    return redirect(url_for('login'))

# Baris ini penting agar Vercel bisa mengenali aplikasi Flask kamu
app = app
