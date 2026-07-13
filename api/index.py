import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import uuid

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

@app.route('/vouchers/unlock/<code_voucher>', methods=['POST'])
def unlock_voucher_data(code_voucher):
    if 'user_id' not in session: return jsonify({"status": "unauthorized"}), 401
    try:
        supabase.table('vouchers').update({"is_locked": False}).eq('voucher_code', code_voucher).execute()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/vouchers/delete/<code_voucher>', methods=['DELETE'])
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
    # Definisikan struktur dasar default agar template HTML tidak kekurangan variabel
    stats_hari = {"Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0}
    sorted_items = []
    max_val = 1  # Nilai default untuk menghindari pembagian dengan angka 0 di HTML

    try:
        # 1. Ambil data mutasi yang berstatus 'Approved' dan berjenis 'Keluar'
        # Gunakan query yang biasa Anda gunakan untuk Supabase
        response = supabase.table('spareparts').select('*').eq('jenis_mutasi', 'Keluar').eq('status_approve', 'Approved').execute()
        mutasi_keluar = response.data if response and hasattr(response, 'data') else []
        
        item_populer = {}

        if mutasi_keluar:
            for item in mutasi_keluar:
                # Ambil jumlah dengan aman, convert ke int
                qty = 0
                try:
                    qty = int(item.get('jumlah', 0))
                except:
                    qty = 0
                    
                nama = item.get('nama_barang', 'Unknown')
                
                # Hitung untuk grafik mingguan berdasarkan tanggal_keluar atau created_at
                tgl_raw = item.get('tanggal_keluar') or item.get('created_at')
                if tgl_raw:
                    try:
                        # Ambil format YYYY-MM-DD
                        date_str = tgl_raw[:10]
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        nama_hari = date_obj.strftime('%A') # Mengeluarkan 'Monday', 'Tuesday', dll
                        
                        if nama_hari in stats_hari:
                            stats_hari[nama_hari] += qty
                    except:
                        pass # Lewati jika format tanggal gagal diparsing
                
                # Hitung item paling banyak keluar
                if nama != 'Unknown':
                    item_populer[nama] = item_populer.get(nama, 0) + qty

            # Ambil 5 item teratas
            sorted_items = sorted(item_populer.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Tentukan nilai tertinggi untuk kalkulasi skala grafik di HTML
            max_val = max(stats_hari.values())
            if max_val < 1:
                max_val = 1

    except Exception as e:
        # Jika ada error database, log dicetak di terminal tapi server tetap jalan aman
        print(f"Error pada Analytics Sparepart: {e}")

    # Kirimkan data ke HTML. Variabel 'max_val' dikirim langsung dari Python agar HTML tidak error
    return render_template('analytics.html', 
                           stats_hari=stats_hari, 
                           item_populer=sorted_items,
                           max_val=max_val)

# --- ACCOUNTING ROUTE (LOG TAGIHAN SUPABASE) ---
@app.route('/accounting', methods=['GET', 'POST'])
def accounting():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
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

    try:
        response = supabase.table('log_tagihan').select("*", count='exact').order('created_at', desc=True).execute()
        db_logs = response.data if response.data else []
        total_logs = response.count if response.count is not None else len(db_logs)
    except Exception as e:
        print(f"Error Fetching Log Tagihan: {e}")
        db_logs, total_logs = [], 0

    return render_template('accounting.html', email=session.get('user_email'), logs=db_logs, total_logs=total_logs)


# =========================================================================
# TAMBAHAN FITUR BARU: ROUTE TICKET & SPAREPART (TERSTRUKTUR & AMAN)
# =========================================================================

@app.route('/tickets', methods=['GET', 'POST'])
def ticket_management():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        nomor_ticket = request.form.get('nomor_ticket').strip()
        if not nomor_ticket:
            timestamp = datetime.now().strftime("%Y%m%d")
            unique_suffix = str(uuid.uuid4().hex[:4]).upper()
            nomor_ticket = f"TCK-{timestamp}-{unique_suffix}"
            
        nama_ticket = request.form.get('nama_ticket')
        priority = request.form.get('priority', 'Normal')
        reporter = request.form.get('reporter')
        eksekutor = request.form.get('eksekutor')
        keterangan = request.form.get('keterangan')
        
        data_ticket = {
            "nomor_ticket": nomor_ticket,
            "nama_ticket": nama_ticket,
            "priority": priority,
            "reporter": reporter,
            "eksekutor": eksekutor if eksekutor else None,
            "keterangan": keterangan,
            "status_ticket": "Open"
        }
        
        try:
            supabase.table('tickets').insert(data_ticket).execute()
            return redirect(url_for('ticket_management'))
        except Exception as e:
            print(f"Error Insert Ticket: {e}")
            return f"Gagal menyimpan data ticket ke database: {e}", 500

    try:
        res_t = supabase.table('tickets').select("*").order('created_at', desc=True).execute()
        db_tickets = res_t.data if res_t.data else []
    except Exception as e:
        print(f"Error Fetching Tickets: {e}")
        db_tickets = []
        
    return render_template('ticket.html', email=session.get('user_email'), tickets=db_tickets)

@app.route('/tickets/update_status/<ticket_id>', methods=['POST'])
def update_ticket_status(ticket_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    new_status = request.form.get('status_ticket')
    try:
        supabase.table('tickets').update({"status_ticket": new_status}).eq('id', ticket_id).execute()
        return redirect(url_for('ticket_management'))
    except Exception as e:
        print(f"Error Update Status Ticket: {e}")
        return f"Gagal mengubah status ticket: {e}", 500


# !!! BAGIAN YANG DIPERBAIKI: INPUT KHUSUS MASUK/KELUAR VIA DROPDOWN & KONDISI USER !!!
@app.route('/spareparts', methods=['GET', 'POST'])
def sparepart_management():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        nama_barang = request.form.get('nama_barang').strip()
        jumlah = int(request.form.get('jumlah', 0))
        satuan = request.form.get('satuan', 'Pcs')
        jenis_mutasi = request.form.get('jenis_mutasi') # 'Masuk' atau 'Keluar'
        tanggal_input = request.form.get('tanggal_mutasi') # Single date input dari form
        
        # Logika pembagian tanggal dan peruntukan user berdasarkan Jenis Mutasi
        if jenis_mutasi == 'Masuk':
            tanggal_masuk = tanggal_input if tanggal_input else None
            tanggal_keluar = None
            untuk_user = "Gudang / Stock" # Otomatis diset ke gudang jika barang masuk
        else:
            tanggal_masuk = None
            tanggal_keluar = tanggal_input if tanggal_input else None
            untuk_user = request.form.get('untuk_user', '').strip()

        data_sparepart = {
            "request_bon": "",  
            "nama_barang": nama_barang,
            "jumlah": jumlah,
            "satuan": satuan,
            "tanggal_masuk": tanggal_masuk,
            "tanggal_keluar": tanggal_keluar,
            "untuk_user": untuk_user,
            "status_approve": "Pending" 
        }
        
        try:
            supabase.table('spareparts').insert(data_sparepart).execute()
            return redirect(url_for('sparepart_management'))
        except Exception as e:
            print(f"Error Insert Sparepart: {e}")
            return f"Gagal menyimpan mutasi sparepart: {e}", 500
            
    try:
        res_s = supabase.table('spareparts').select("*").order('created_at', desc=True).execute()
        db_spareparts = res_s.data if res_s.data else []
    except Exception as e:
        print(f"Error Fetching Spareparts: {e}")
        db_spareparts = []
        
    return render_template('sparepart.html', email=session.get('user_email'), spareparts=db_spareparts)

@app.route('/spareparts/approve/<int:item_id>', methods=['POST'])
def approve_sparepart(item_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        # 1. Ambil info item mutasi yang akan di-approve
        target_res = supabase.table('spareparts').select("*").eq('id', item_id).execute()
        if target_res.data:
            item = target_res.data[0]
            nama_barang = item.get('nama_barang')
            jumlah = int(item.get('jumlah', 0))
            satuan = item.get('satuan', 'Pcs')
            tgl_masuk = item.get('tanggal_masuk')
            tgl_keluar = item.get('tanggal_keluar')

            # 2. Ambil master data untuk menghitung sinkronisasi stok ter-update
            check_master = supabase.table('master_spareparts').select("*").eq('nama_barang', nama_barang).execute()
            
            if tgl_masuk and not tgl_keluar:
                # KONDISI BARANG MASUK -> Tambah Stok di Master
                if check_master.data:
                    stok_baru = int(check_master.data[0].get('stok_sekarang', 0)) + jumlah
                    supabase.table('master_spareparts').update({"stok_sekarang": stok_baru}).eq('nama_barang', nama_barang).execute()
                else:
                    supabase.table('master_spareparts').insert({"nama_barang": nama_barang, "stok_sekarang": jumlah, "satuan": satuan}).execute()
            
            elif tgl_keluar:
                # KONDISI BARANG KELUAR -> Potong Stok di Master
                if check_master.data:
                    stok_baru = int(check_master.data[0].get('stok_sekarang', 0)) - jumlah
                    if stok_baru < 0: 
                        stok_baru = 0  # Mengunci batas minimum stok agar tidak minus
                    supabase.table('master_spareparts').update({"stok_sekarang": stok_baru}).eq('nama_barang', nama_barang).execute()
                else:
                    # Inisialisasi master barang baru dengan stok 0 jika belum ada data sebelumnya
                    supabase.table('master_spareparts').insert({"nama_barang": nama_barang, "stok_sekarang": 0, "satuan": satuan}).execute()

        # 3. Ubah status data mutasi di log menjadi Approved
        supabase.table('spareparts').update({"status_approve": "Approved"}).eq('id', item_id).execute()
        return redirect(url_for('sparepart_management'))
    except Exception as e:
        print(f"Error Approve Sparepart: {e}")
        return f"Gagal memproses approval: {e}", 500


# ==========================================
# RUTE UNTUK MENANGANI REJECT MUTASI SPAREPART
# ==========================================
@app.route('/spareparts/reject/<int:item_id>', methods=['POST'])
def reject_sparepart(item_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        # Jika ditolak (Rejected), status langsung berubah tanpa mempengaruhi hitungan stok di master
        supabase.table('spareparts').update({"status_approve": "Rejected"}).eq('id', item_id).execute()
        return redirect(url_for('sparepart_management'))
    except Exception as e:
        print(f"Error Reject Sparepart: {e}")
        return f"Gagal menolak sparepart: {e}", 500

@app.route('/spareparts/master', methods=['GET'])
def sparepart_master():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    try:
        # Ambil data dari tabel master_spareparts
        res_m = supabase.table('master_spareparts').select("*").order('nama_barang', desc=False).execute()
        db_master = res_m.data if res_m.data else []
    except Exception as e:
        print(f"Error Fetching Master Spareparts: {e}")
        db_master = []
        
    return render_template('sparepart_master.html', email=session.get('user_email'), master_stock=db_master)

# =========================================================================


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
        existing = supabase.table('users').select('id').eq('email', email).execute()
        if existing.data:
            return jsonify({'error': 'Email sudah terdaftar'}), 409

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
