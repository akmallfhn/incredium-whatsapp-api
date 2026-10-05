-- Pisahkan data lead ke wa_leads dengan stage per tenant; aman diulang, kolom lama belum di-drop.

BEGIN;

------------
-- Tables --
------------

CREATE TABLE IF NOT EXISTS wa_lead_stages (
  id           CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  tenant_id    CHAR(21)     NOT NULL     REFERENCES tenants (id),
  key          VARCHAR      NOT NULL,
  name         VARCHAR      NOT NULL,
  description  TEXT             NULL,
  position     SMALLINT     NOT NULL,
  status       status_enum  NOT NULL     DEFAULT 'active',
  created_at   TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tenant_id, key),
  UNIQUE (tenant_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS wa_leads (
  conv_id                 CHAR(21)      PRIMARY KEY  REFERENCES wa_conversations (id) ON DELETE CASCADE,
  stage_id                CHAR(21)          NULL     REFERENCES wa_lead_stages (id),
  handler_id              UUID              NULL     REFERENCES users (id),
  mode                    wa_mode_enum  NOT NULL     DEFAULT 'human',
  is_internal             BOOLEAN       NOT NULL     DEFAULT false,
  brand_name              VARCHAR           NULL,
  project_value           BIGINT            NULL,
  winning_rate            SMALLINT      NOT NULL     DEFAULT 0,
  note                    VARCHAR           NULL,
  evaluated_last_chat_id  CHAR(21)          NULL     REFERENCES wa_chats (id),
  created_at              TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at              TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

-------------
-- Indexes --
-------------

CREATE INDEX IF NOT EXISTS wa_chats_conv_id_created_at_idx  ON wa_chats (conv_id, created_at DESC);
-- Awalan (conv_id) sudah tercakup index di atas.
DROP INDEX IF EXISTS wa_chats_conv_id_idx;

CREATE INDEX IF NOT EXISTS wa_leads_stage_id_idx         ON wa_leads (stage_id);
CREATE INDEX IF NOT EXISTS wa_leads_brand_name_trgm_idx  ON wa_leads USING gin (brand_name gin_trgm_ops);

----------
-- Data --
----------

-- Setiap tenant mendapat lima stage dari wa_lead_status_enum; deskripsinya kriteria lama prompt Lead Evaluation.
INSERT INTO wa_lead_stages (tenant_id, key, name, description, position)
SELECT t.id, s.key, s.name, s.description, s.position
FROM tenants t
CROSS JOIN (
  VALUES
    ('cold', 'Cold', 'Pesan baru, kebutuhan belum jelas, atau bukan tawaran kerja sama sama sekali.', 1),
    ('qualified', 'Qualified', 'Kebutuhan sudah jelas (ada brand, acara, tanggal, atau format kerja sama), tapi rate card atau penawaran harga belum dikirim.', 2),
    ('rate_card_sent', 'Rate Card Sent', 'Rate card, pricelist, atau penawaran harga sudah dikirim ke pihak brand.', 3),
    ('negotiation', 'Negotiation', 'Sedang tawar-menawar harga atau ruang lingkup pekerjaan.', 4),
    ('closed', 'Closed', 'Deal sudah disepakati, tinggal eksekusi, atau acaranya sudah berjalan.', 5)
) AS s (key, name, description, position)
ON CONFLICT (tenant_id, key) DO NOTHING;

-- Satu baris wa_leads per percakapan; percakapan yang sudah punya baris tidak disentuh.
INSERT INTO wa_leads (
  conv_id, stage_id, handler_id, mode, is_internal,
  brand_name, project_value, winning_rate, note, created_at, updated_at
)
SELECT
  v.id, s.id, v.handler_id, v.mode, v.is_internal,
  v.brand_name, v.project_value, v.winning_rate, v.note, v.created_at, v.updated_at
FROM wa_conversations v
LEFT JOIN wa_lead_stages s ON s.tenant_id = v.tenant_id AND s.key = v.lead_status::text
ON CONFLICT (conv_id) DO NOTHING;

-- Batalkan seluruh migrasi kalau ada percakapan yang tidak tersalin atau kehilangan stage.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM wa_conversations v
    LEFT JOIN wa_leads l ON l.conv_id = v.id
    WHERE l.conv_id IS NULL
       OR NOT EXISTS (
         SELECT 1 FROM wa_lead_stages s
         WHERE s.tenant_id = v.tenant_id AND s.key = v.lead_status::text
       )
  ) THEN
    RAISE EXCEPTION 'wa_leads tidak lengkap: ada percakapan tanpa baris atau tanpa stage padanan';
  END IF;
END $$;

COMMIT;
