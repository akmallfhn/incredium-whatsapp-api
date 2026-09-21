-- Migrasi: jadikan wam_id identitas satu pesan di wa_chats
--
-- Sudah dijalankan di Supabase Incredium 2026-09-21; dua fase, wajib berurutan.

-- Fase 1: arsipkan dulu semua baris yang terlibat duplikat, sebelum apa pun dihapus.
CREATE TABLE wa_chats_dupe_backup_20260921 AS
SELECT c.*,
       row_number() OVER (
         PARTITION BY c.wam_id
         ORDER BY (c.message <> '' OR c.attachment IS NOT NULL) DESC, c.created_at, c.id
       ) = 1 AS keep
FROM wa_chats c
WHERE c.wam_id IN (SELECT wam_id FROM wa_chats GROUP BY wam_id HAVING count(*) > 1);

-- Fase 2: rencana dibaca dari arsip, bukan dihitung ulang, supaya tidak bergeser di tengah jalan.

-- Status terjauh dari seluruh kembaran dipindahkan ke baris yang dipertahankan.
WITH merged AS (
  SELECT wam_id,
         (array_agg(status ORDER BY CASE status
            WHEN 'failed' THEN 4 WHEN 'read' THEN 3 WHEN 'delivered' THEN 2 WHEN 'sent' THEN 1
            ELSE 0 END DESC) FILTER (WHERE status IS NOT NULL))[1] AS status,
         min(sent_at)      AS sent_at,
         min(delivered_at) AS delivered_at,
         min(read_at)      AS read_at,
         min(failed_at)    AS failed_at
  FROM wa_chats_dupe_backup_20260921
  GROUP BY wam_id
)
UPDATE wa_chats k
SET status       = COALESCE(k.status, m.status),
    sent_at      = COALESCE(k.sent_at, m.sent_at),
    delivered_at = COALESCE(k.delivered_at, m.delivered_at),
    read_at      = COALESCE(k.read_at, m.read_at),
    failed_at    = COALESCE(k.failed_at, m.failed_at),
    updated_at   = CURRENT_TIMESTAMP
FROM merged m, wa_chats_dupe_backup_20260921 b
WHERE b.wam_id = m.wam_id AND b.keep AND k.id = b.id;

-- Balasan yang menunjuk baris buangan dialihkan ke baris yang dipertahankan.
UPDATE wa_chats c
SET reply_to_id = k.id,
    updated_at  = CURRENT_TIMESTAMP
FROM wa_chats_dupe_backup_20260921 loser
JOIN wa_chats_dupe_backup_20260921 k ON k.wam_id = loser.wam_id AND k.keep
WHERE c.reply_to_id = loser.id AND NOT loser.keep;

-- Penanda batas baca percakapan juga FK ke wa_chats, jadi ikut dialihkan.
UPDATE wa_conversations wc
SET last_read_id = k.id,
    updated_at   = CURRENT_TIMESTAMP
FROM wa_chats_dupe_backup_20260921 loser
JOIN wa_chats_dupe_backup_20260921 k ON k.wam_id = loser.wam_id AND k.keep
WHERE wc.last_read_id = loser.id AND NOT loser.keep;

DELETE FROM wa_chats WHERE id IN (SELECT id FROM wa_chats_dupe_backup_20260921 WHERE NOT keep);

-- Constraint, bukan index lepas: objeknya sama dengan UNIQUE inline di incredium.sql.
ALTER TABLE wa_chats ADD CONSTRAINT wa_chats_wam_id_key UNIQUE (wam_id);
