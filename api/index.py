import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Path Management
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

# --- AUTH ROUTES ---

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
        res_v = supabase.table('vouchers').select("*", count='exact').execute()
        db_vouchers = res_v.data if res_v.data else []
        total_v = res_v.count if res_v.count is not None else len(db_vouchers)
        res_s = supabase.table('sales_activity').select("*").order('tanggal', desc=True).limit(10).execute()
        db_sales = res_s.data if res_s.data else []
    except Exception as e:
        print(f"Dashboard Error: {e}")
        db_vouchers, db_sales, total_v = [], [], 0
    return render_template('dashboard.html', email=session.get('user_email'), vouchers=db_vouchers, total_vouchers=total_v, activity_data=db_sales)

# --- SALES MANAGEMENT ---

@app.route('/sales')
def sales():
    if 'user_id' not in session: return redirect(url_for('login'))
    sales_filter = request.args.get('sales_filter')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        master_res = supabase.table('sales_activity').select("nama_customer").execute()
        unique_customers = []
        seen = set()
        for item in (master_res.data or []):
            name = item['nama_customer']
            if name not in seen:
                unique_customers.append({"nama_customer": name})
                seen.add(name)
        query = supabase.table('sales_activity').select("*")
        if sales_filter: query = query.ilike('nama_sales', f'%{sales_filter}%')
        if start_date: query = query.gte('tanggal', start_date)
        if end_date: query = query.lte('tanggal', end_date)
        response = query.order('tanggal', desc=True).execute()
        db_sales = response.data if response.data else []
        summary = {}
        for item in db_sales:
            name = item.get('nama_sales', 'Unknown')
            summary[name] = summary.get(name, 0) + 1
        stats = [{"nama_sales": k, "total_customer": v} for k, v in summary.items()]
    except Exception as e: 
        db_sales, stats, unique_customers = [], [], []
        print(f"Error Sales: {e}")
    return render_template('sales.html', email=session.get('user_email'), activity_data=db_sales, summary_stats=stats, master_customers=unique_customers)

@app.route('/sales/add', methods=['POST'])
def add_sales():
    if 'user_id' not in session: return redirect(url_for('login'))
    data = {"hari": request.form.get('hari'), "tanggal": request.form.get('tanggal'), "nama_sales": request.form.get('nama_sales'), "nama_customer": request.form.get('nama_customer'), "alamat_customer": request.form.get('alamat_customer')}
    try:
        supabase.table('sales_activity').insert(data).execute()
        return redirect(url_for('sales'))
    except Exception as e: return f"Gagal simpan: {e}", 500

@app.route('/sales/update', methods=['POST'])
def update_sales():
    if 'user_id' not in session: return redirect(url_for('login'))
    row_id = request.form.get('id')
    data = {"hari": request.form.get('hari'), "tanggal": request.form.get('tanggal'), "nama_sales": request.form.get('nama_sales'), "nama_customer": request.form.get('nama_customer'), "alamat_customer": request.form.get('alamat_customer')}
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

# --- VOUCHER MANAGEMENT ---

@app.route('/vouchers', methods=['GET', 'POST'])
def vouchers():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        try:
            supabase.table('vouchers').insert({"user_name": data.get('user_name', 'Guest'), "voucher_code": data.get('voucher_code'), "location": data.get('location', 'Office'), "speed": "15Mbps", "status": "Active", "is_locked": False}).execute()
            return jsonify({"status": "success"}), 200
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    try:
        response = supabase.table('vouchers').select("*").order('created_at', desc=True).execute()
        db_vouchers = response.data if response.data else []
    except: db_vouchers = []
    return render_template('vouchers.html', email=session.get('user_email'), vouchers=db_vouchers)

@app.route('/vouchers/update_lock', methods=['POST'])
def update_voucher_lock():
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    code = data.get('voucher_code')
    raw_status = data.get('is_locked')
    new_status = True if str(raw_status).lower() == 'true' else False
    try:
        supabase.table('vouchers').update({"is_locked": new_status}).eq('voucher_code', code).execute()
        return jsonify({"status": "success", "new_status": new_status}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# TAMBAHAN BARU: Route untuk Update Voucher via Form Edit di Front-End
@app.route('/vouchers/update/<code_voucher>', methods=['POST'])
def update_voucher_data(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    user_name = data.get('user_name')
    location = data.get('location')
    try:
        supabase.table('vouchers').update({"user_name": user_name, "location": location}).eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# TAMBAHAN BARU: Route untuk Unlock Voucher
@app.route('/vouchers/unlock/<code_voucher>', methods=['POST'])
def unlock_voucher_data(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('vouchers').update({"is_locked": False}).eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# TAMBAHAN BARU: Route untuk Delete Voucher
@app.route('/vouchers/delete/<code_voucher>', methods=['`DELETE`', 'DELETE'])
def delete_voucher_data(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('vouchers').delete().eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# --- API FOR CLAIM PAGE ---

@app.route('/claim')
def claim_page():
    return render_template('claim.html')

@app.route('/api/get-voucher', methods=['POST'])
def get_voucher_api():
    data = request.get_json(silent=True) or {}
    user_name = data.get('user_name', '').strip()
    if not user_name: return jsonify({"status": "error", "message": "Nama harus diisi"}), 400
    try:
        response = supabase.table('vouchers').select("*").eq('user_name', user_name).limit(1).execute()
        if response.data:
            v = response.data[0]
            lock_val = v.get('is_locked')
            if lock_val is True or str(lock_val).lower() == 'true':
                return jsonify({"status": "error", "message": "Terblokir"}), 403
            return jsonify({"status": "success", "data": v}), 200
        return jsonify({"status": "error", "message": "Not Found"}), 404
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/lock-voucher', methods=['POST'])
def lock_voucher_api():
    data = request.get_json(silent=True) or {}
    row_id = data.get('id')
    if not row_id: return jsonify({"status": "error", "message": "ID Missing"}), 400
    try:
        supabase.table('vouchers').update({"is_locked": True}).eq('id', row_id).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# --- SETTINGS, ANALYTICS & LOGOUT ---

@app.route('/settings')
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html', email=session.get('user_email'), user_id=session.get('user_id'))

@app.route('/analytics')
def analytics():
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        response = supabase.table('vouchers').select("id", count='exact').execute()
        total_vouchers = response.count if response.count is not None else 0
    except: total_vouchers = 0
    return render_template('analytics.html', email=session.get('user_email'), total_vouchers=total_vouchers)

# --- TAMBAHAN BARU: ACCOUNTING ROUTE (LOG TAGIHAN SUPABASE) ---
@app.route('/accounting', methods=['GET', 'POST'])
def accounting():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Penambahan log baru (Prinsip: Hanya insert data baru, tidak merusak data lama)
        data = {
            "bulan_tahun": request.form.get('bulan_tahun'),
            "nomor_telepon": request.form.get('nomor_telepon'),
            "pemilik": request.form.get('pemilik'),
            "nominal_pembayaran": float(request.form.get('nominal_pembayaran', 0))
        }
        try:
            supabase.table('log_tagihan').insert(data).execute()
            return redirect(url_for('accounting'))
        except Exception as e:
            return f"Gagal menyimpan data log tagihan: {e}", 500

    # Ambil data log historis dari Supabase tabel 'log_tagihan'
    try:
        response = supabase.table('log_tagihan').select("*", count='exact').order('created_at', desc=True).execute()
        db_logs = response.data if response.data else []
        total_logs = response.count if response.count is not None else len(db_logs)
    except Exception as e:
        print(f"Error Fetching Log Tagihan: {e}")
        db_logs, total_logs = [], 0

    return render_template('accounting.html', email=session.get('user_email'), logs=db_logs, total_logs=total_logs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# === USER MANAGEMENT ===
@app.route('/add_user', methods=['POST'])
def add_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'operator')

    if not email or not password:
        return jsonify({'error': 'Email dan password wajib diisi'}), 400

    try:
        # Cek apakah email sudah ada
        existing = supabase.table('users').select('id').eq('email', email).execute()
        if existing.data:
            return jsonify({'error': 'Email sudah terdaftar'}), 409

        # Hash password (pakai werkzeug seperti di auth)
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(password)

        new_user = {
            "email": email,
            "password": hashed_password,
            "role": role,
            "is_active": True
        }

        response = supabase.table('users').insert(new_user).execute()

        if response.data:
            return jsonify({
                'message': 'User berhasil dibuat',
                'email': email
            }), 201
        else:
            return jsonify({'error': 'Gagal membuat user'}), 500

    except Exception as e:
        print(f"Add User Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
