import os
import sys

# FIX: Tambahkan path agar folder 'modules' bisa terbaca oleh Vercel
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from modules.auth import login_user, logout_user
from modules.supabase_db import supabase  

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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        response = supabase.table('vouchers').select("id", count='exact').execute()
        total_vouchers = response.count if response.count else 0
    except:
        total_vouchers = 0

    return render_template('analytics.html', 
                           email=session.get('user_email'), 
                           total_vouchers=total_vouchers)

@app.route('/vouchers', methods=['GET', 'POST'])
def vouchers():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = request.json
        try:
            # REVISI: Tambahkan field 'location' agar tersimpan di Supabase
            supabase.table('vouchers').insert({
                "user_name": data.get('user_name'),
                "voucher_code": data.get('voucher_code'),
                "location": data.get('location'),
                "speed": "10Mbps",
                "status": "Active"
            }).execute()
            return {"status": "success"}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

    # Ambil data voucher terbaru
    try:
        response = supabase.table('vouchers').select("*").order('created_at', desc=True).execute()
        db_vouchers = response.data if response.data else []
    except Exception:
        db_vouchers = []
    
    return render_template('vouchers.html', 
                           email=session.get('user_email'),
                           vouchers=db_vouchers)

# TAMBAHKAN: Route untuk menghapus voucher di database
@app.route('/vouchers/delete/<code_voucher>', methods=['DELETE'])
def delete_voucher(code_voucher):
    if 'user_id' not in session:
        return {"status": "unauthorized"}, 401
    try:
        supabase.table('vouchers').delete().eq('voucher_code', code_voucher).execute()
        return {"status": "success"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/settings')
def settings():
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
