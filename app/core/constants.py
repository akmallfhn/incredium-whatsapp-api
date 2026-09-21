"""Nilai tetap yang dulunya env var. Mengubahnya keputusan kode, bukan konfigurasi deployment."""

# Bucket attachment WhatsApp, sama dengan yang dibaca UI; menggantinya migrasi file.
SUPABASE_BUCKET = "pureva"

# Zona waktu bucket harian & heatmap statistik. Request boleh menimpanya lewat `timezone`.
STAT_TIMEZONE = "Asia/Jakarta"

# Umur JWT sesi login sejak diterbitkan.
JWT_TTL_DAYS = 365

# Provider LLM utama. Eksplisit, bukan ditebak dari key yang terisi.
LLM_PROVIDER = "openai"

# Ceiling upload Supabase Storage; PDF di atas ini diperkecil dulu, bukan ditolak.
SUPABASE_MAX_OBJECT_BYTES = 45 * 1024 * 1024

# Jeda sweeper yang menyelesaikan event webhook yang belum diproses.
WEBHOOK_SWEEP_INTERVAL_SECONDS = 60

# Banyak event yang diambil sweeper per putaran.
WEBHOOK_DRAIN_BATCH = 20

# Batas percobaan satu event; lewat ini ditandai failed supaya tidak diulang selamanya.
WEBHOOK_EVENT_MAX_ATTEMPTS = 5

# Event yang masih processing lebih lama dari ini dianggap macet dan diambil alih sweeper.
WEBHOOK_EVENT_STUCK_MINUTES = 5

# Umur simpan event yang sudah done; dibuang sweeper supaya tabelnya tidak tumbuh selamanya.
WEBHOOK_EVENT_RETENTION_DAYS = 14
