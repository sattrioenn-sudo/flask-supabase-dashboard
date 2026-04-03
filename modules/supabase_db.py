import os
from supabase import create_client, Client

# Kita gunakan os.environ agar lebih aman saat di-deploy ke Vercel nanti
# URL dan KEY ini bisa kamu dapatkan di Settings > API di dashboard Supabase-mu
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

def get_client() -> Client:
    """Fungsi untuk memanggil client Supabase secara global"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        # Ini untuk handle jika lupa pasang Environment Variables
        raise ValueError("Supabase URL atau Key belum dikonfigurasi!")
        
    return create_client(SUPABASE_URL, SUPABASE_KEY)
