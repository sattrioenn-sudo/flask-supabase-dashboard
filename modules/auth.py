from modules.supabase_db import get_client

# Inisialisasi client dari file yang kita buat sebelumnya
supabase = get_client()

def login_user(email, password):
    """
    Fungsi untuk memverifikasi email dan password ke Supabase Auth.
    Mengembalikan data user jika berhasil, atau pesan error jika gagal.
    """
    try:
        # Mencoba melakukan sign in
        response = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })
        
        # Jika berhasil, kembalikan data user dan None (tidak ada error)
        return response.user, None
        
    except Exception as e:
        # Jika gagal (password salah/user tidak ada), kembalikan None dan pesan error
        error_message = str(e)
        return None, error_message

def logout_user():
    """
    Fungsi untuk mengakhiri sesi di sisi Supabase.
    """
    try:
        supabase.auth.sign_out()
        return True
    except:
        return False
