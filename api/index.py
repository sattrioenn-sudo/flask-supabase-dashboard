import os
import sys

# FIX: Tambahkan path agar folder 'modules' bisa terbaca oleh Vercel
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, render_template, request, redirect, url_for, session, flash
from modules.auth import login_user, logout_user

# Konfigurasi Flask
app = Flask(__name__, 
            template_folder='../templates', 
            static_folder='../static')

# Secret key untuk session browser
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key-yang-sangat-rahasia")

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user, error = login_user(email, password)
        
        if user:
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('dashboard'))
        else:
            flash(f"Login Gagal: {error}", "danger")
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', email=session.get('user_email'))

@app.route('/analytics')
def analytics():
    """Halaman Analytics"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('analytics.html', email=session.get('user_email'))

@app.route('/vouchers')
def vouchers():
    """Route Baru: Manajemen Voucher WiFi"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Data dummy voucher untuk ditampilkan di templates/vouchers.html
    active_vouchers = [
        {"code": "NEX-2026-X1", "speed": "10Mbps", "status": "Active"},
        {"code": "NEX-2026-X2", "speed": "10Mbps", "status": "Active"},
        {"code": "NEX-2026-Z9", "speed": "5Mbps", "status": "Expired"}
    ]
    
    return render_template('vouchers.html', 
                           email=session.get('user_email'),
                           vouchers=active_vouchers)

@app.route('/settings')
def settings():
    """Halaman Settings"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html', 
                           email=session.get('user_email'), 
                           user_id=session.get('user_id'))

@app.route('/logout')
def logout():
    session.clear()
    try:
        logout_user()
    except:
        pass
    return redirect(url_for('login'))

# WAJIB UNTUK VERCEL
app = app
