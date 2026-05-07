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

# --- BAGIAN SALES (UPDATE TERBARU) ---

@app.route('/sales')
def sales():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Ambil parameter filter untuk fitur Rekap
    sales_filter = request.args.get('sales_filter')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        # 1. Master Customer: Mengambil list nama customer unik untuk autocomplete
        master_res = supabase.table('sales_activity').select("nama_customer").execute()
        unique_customers = []
        seen = set()
        for item in (master_res.data or []):
            name = item['nama_customer']
            if name not in seen:
                unique_customers.append({"nama_customer": name})
                seen.add(name)

        # 2. Query Utama dengan Filter Rekap
        query = supabase.table('sales_activity').select("*")
        
        if sales_filter:
            query = query.ilike('nama_sales', f'%{sales_filter}%')
        if start_date:
            query = query.gte('tanggal', start_date)
        if end_date:
            query = query.lte('tanggal', end_date)
            
        response = query.order('tanggal', desc=True).execute()
        db_sales = response.data if response.data else []
        
        # 3. Hitung Statistik untuk Panel Ringkasan
        summary = {}
        for item in db_sales:
            name = item.get('nama_sales', 'Unknown')
            summary[name] = summary.get(name, 0) + 1
        stats = [{"nama_sales": k, "total_customer": v} for k, v in summary.items()]
        
    except Exception as e: 
        db_sales, stats, unique_customers = [], [], []
        print(f"Error Sales: {e}")
        
    return render_template('sales.html', 
                           email=session.get('user_email'), 
                           activity_data=db_sales, 
                           summary_stats=stats,
                           master_customers=unique_customers)

@app.route('/sales/add', methods=['POST'])
def add_sales():
    if 'user_id' not in session: return redirect(url_for('login'))
    data = {
        "hari": request.form.get('hari'),
        "tanggal": request.form.get('tanggal'),
        "nama_sales": request.form.get('nama_sales'),
        "nama_customer": request.form.get('nama_customer'),
        "alamat_customer": request.form.get('alamat_customer')
    }
    try:
        supabase.table('sales_activity').insert(data).execute()
        return redirect(url_for('sales'))
    except Exception as e: return f"Gagal simpan: {e}", 500

@app.route('/sales/update', methods=['POST'])
def update_sales():
    """Fungsi untuk edit data yang sudah ada"""
    if 'user_id' not in session: return redirect(url_for('login'))
    row_id = request.form.get('id')
    data = {
        "hari": request.form.get('hari'),
        "tanggal": request.form.get('tanggal'),
        "nama_sales": request.form.get('nama_sales'),
        "nama_customer": request.form.get('nama_customer'),
        "alamat_customer": request.form.get('alamat_customer')
    }
    try:
        supabase.table('sales_activity').update(data).eq('id', row_id).execute()
        return redirect(url_for('sales'))
    except Exception as e: return f"Gagal update: {e}", 500

@app.route('/sales/delete/<id>', methods=['DELETE'])
def delete_sales(id):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('sales_activity').delete().eq('id', id).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sales/recap', methods=['GET'])
def sales_recap():
    """Alias route untuk filter rekap"""
    return sales()

# --- BAGIAN VOUCHER & API (TIDAK BERUBAH) ---

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
                "speed": "15Mbps", "status": "Active", "is_locked": False 
            }).execute()
            return jsonify({"status": "success"}), 200
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    try:
        response = supabase.table('vouchers').select("*").order('created_at', desc=True).execute()
        db_vouchers = response.data if response.data else []
    except: db_vouchers = []
    return render_template('vouchers.html', email=session.get('user_email'), vouchers=db_vouchers)

@app.route('/vouchers/delete/<code_voucher>', methods=['DELETE'])
def delete_voucher(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('vouchers').delete().eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/analytics')
def analytics():
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        response = supabase.table('vouchers').select("id", count='exact').execute()
        total_vouchers = response.count if response.count else 0
    except: total_vouchers = 0
    return render_template('analytics.html', email=session.get('user_email'), total_vouchers=total_vouchers)

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
            if v.get('is_locked'): return jsonify({"status": "error", "message": "Terblokir"}), 403
            return jsonify({"status": "success", "data": v}), 200
        return jsonify({"status": "error", "message": "Not Found"}), 404
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
