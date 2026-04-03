import os
from supabase import create_client, Client

# Ambil URL dan Key dari Environment Variables Vercel
# Gunakan SUPABASE_KEY (Anon Key) atau SERVICE_KEY sesuai yang kamu set di Vercel
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Biar tidak bingung kalau lupa pasang Env di Vercel
    raise ValueError("API Key atau URL Supabase belum terpasang di Environment Variables!")

# Langsung definisikan variabel 'supabase' agar bisa di-import oleh api/index.py
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_client() -> Client:
    """Fungsi ini tetap dipertahankan agar tidak merusak fungsi lain jika ada yang memanggilnya"""
    return supabase
