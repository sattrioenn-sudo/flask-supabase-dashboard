import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# FIX: Path agar folder 'modules' terbaca di Vercel
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from modules.auth import login_user, logout_user
from modules.supabase_db import supabase  

app = Flask(__name__, 
            template_folder='../templates', 
            static_folder='../static')

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key-yang-sangat-rahasia")

@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
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
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        response = supabase.table('vouchers').select("*").execute()
        db_vouchers = response.data if response.data else []
    except: db_vouchers = []
    return render_template('dashboard.html', email=session.get('user_email'), vouchers=db_vouchers)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        response = supabase.table('vouchers').select("id", count='exact').execute()
        total_vouchers = response.count if response.count else 0
    except: total_vouchers = 0
    return render_template('analytics.html', email=session.get('user_email'), total_vouchers=total_vouchers)

@app.route('/vouchers', methods=['GET', 'POST'])
def vouchers():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        try:
            supabase.table('vouchers').insert({
                "user_name": data.get('user_name', 'Guest'),
                "voucher_code": data.get('voucher_code'),
                "location": data.get('location', 'Office'),
                "speed": "15Mbps",
                "status": "Active",
                "is_locked": False 
            }).execute()
            return jsonify({"status": "success"}), 200
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    try:
        response = supabase.table('vouchers').select("*").order('created_at', desc=True).execute()
        db_vouchers = response.data if response.data else []
    except: db_vouchers = []
    return render_template('vouchers.html', email=session.get('user_email'), vouchers=db_vouchers)

# --- TAMBAHAN ROUTE SALES BARU ---
@app.route('/sales')
def sales():
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        # Mengambil data sales dari Supabase
        response = supabase.table('sales').select("*").order('created_at', desc=True).execute()
        db_sales = response.data if response.data else []
    except: 
        db_sales = []
    return render_template('sales.html', email=session.get('user_email'), sales=db_sales)
# ---------------------------------

@app.route('/vouchers/delete/<code_voucher>', methods=['DELETE'])
def delete_voucher(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('vouchers').delete().eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/vouchers/unlock/<code_voucher>', methods=['POST'])
def unlock_voucher(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('vouchers').update({"is_locked": False}).eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/claim')
def claim_page():
    target_user = request.args.get('u', '')
    return render_template('claim.html', target_user=target_user)

@app.route('/api/get-voucher', methods=['POST'])
def get_voucher_api():
    data = request.get_json(silent=True) or {}
    user_name = data.get('user_name', '').strip()
    if not user_name: return jsonify({"status": "error", "message": "Nama harus diisi"}), 400
    try:
        response = supabase.table('vouchers').select("*").eq('user_name', user_name).limit(1).execute()
        if response.data:
            v = response.data[0]
            if v.get('is_locked'):
                return jsonify({"status": "error", "message": "Voucher sudah diklaim. Hubungi Admin."}), 403
            return jsonify({"status": "success", "data": v}), 200
        return jsonify({"status": "error", "message": "Nama tidak ditemukan"}), 404
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/lock-voucher', methods=['POST'])
def lock_voucher_api():
    data = request.get_json(silent=True) or {}
    v_id = data.get('id')
    try:
        supabase.table('vouchers').update({"is_locked": True}).eq('id', v_id).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/settings')
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html', email=session.get('user_email'), user_id=session.get('user_id'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
