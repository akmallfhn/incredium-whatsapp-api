"""Nilai tetap yang dulunya env var. Mengubahnya keputusan kode, bukan konfigurasi deployment."""

# Bucket attachment WhatsApp, sama dengan yang dibaca UI; menggantinya migrasi file.
SUPABASE_BUCKET = "pureva"

# Zona waktu bucket harian & heatmap statistik. Request boleh menimpanya lewat `timezone`.
STAT_TIMEZONE = "Asia/Jakarta"

# Umur JWT sesi login sejak diterbitkan.
JWT_TTL_DAYS = 365

# Provider LLM utama. Eksplisit, bukan ditebak dari key yang terisi.
LLM_PROVIDER = "openai"

# Satu model untuk semua node fallback: yang dikejar ketersediaan, bukan kualitas maksimal.
ANTHROPIC_FALLBACK_MODEL = "claude-haiku-4-5-20251001"
