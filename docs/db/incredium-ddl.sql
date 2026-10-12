-- PostgreSQL Database for Incredium

------------------
-- Enumerations --
------------------

-- Enumeration for the users, tenants, meta_apps, and meta_connections tables

CREATE TYPE status_enum AS ENUM (
  'active',
  'inactive'
);

-- Enumeration for the users table

CREATE TYPE user_role_enum AS ENUM (
  'Super Admin',
  'Administrator',
  'Member'
);

-- Enumeration for the wa_leads table (wa_*)

CREATE TYPE wa_mode_enum AS ENUM (
  'ai',
  'human'
);

-- Enumeration for the wa_chats table (wac_*)

CREATE TYPE wac_direction_enum AS ENUM (
  'inbound',
  'outbound'
);

CREATE TYPE wac_sender_type_enum AS ENUM (
  'user',
  'admin',
  'agent'
);

CREATE TYPE wac_type_enum AS ENUM (
  'audio',
  'button',
  'contacts',
  'document',
  'edit',
  'image',
  'interactive',
  'location',
  'order',
  'reaction',
  'revoke',
  'sticker',
  'system',
  'text',
  'unsupported',
  'video',
  'template'
);

CREATE TYPE wac_status_enum AS ENUM (
  'sent',
  'delivered',
  'read',
  'failed'
);

-- Enumeration for the wa_webhook_events table (wwe_*)

CREATE TYPE wwe_status_enum AS ENUM (
  'pending',
  'processing',
  'done',
  'ignored',
  'failed'
);

------------
-- Tables --
------------

-- User data

CREATE TABLE users (
  id             UUID            PRIMARY KEY  DEFAULT gen_random_uuid(),
  full_name      VARCHAR         NOT NULL,
  email          VARCHAR         NOT NULL     UNIQUE,
  avatar         VARCHAR             NULL,
  role           user_role_enum  NOT NULL     DEFAULT 'Member',
  password_hash  TEXT                NULL,
  status         status_enum     NOT NULL     DEFAULT 'active',
  created_at     TIMESTAMPTZ     NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMPTZ     NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tokens (
  id          SERIAL       PRIMARY KEY,
  user_id     UUID         NOT NULL,
  is_active   BOOLEAN      NOT NULL  DEFAULT TRUE,
  token       TEXT         NOT NULL  UNIQUE,
  expires_at  TIMESTAMPTZ  NOT NULL,
  created_at  TIMESTAMPTZ  NOT NULL  DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users_access (
  id          SERIAL       PRIMARY KEY,
  user_id     UUID         NOT NULL,
  tenant_id   CHAR(21)     NOT NULL,
  created_at  TIMESTAMPTZ  NOT NULL  DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, tenant_id)
);

-- Tenants

CREATE TABLE tenants (
  id               CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  name             VARCHAR      NOT NULL,
  slug             VARCHAR      NOT NULL     UNIQUE,
  status           status_enum  NOT NULL     DEFAULT 'active',
  active_agent_id  CHAR(21)         NULL,
  created_at       TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

-- Meta WhatsApp connections

CREATE TABLE meta_apps (
  id                    CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  name                  VARCHAR      NOT NULL,
  app_id                VARCHAR      NOT NULL     UNIQUE,
  app_secret            TEXT         NOT NULL,
  webhook_verify_token  TEXT         NOT NULL,
  status                status_enum  NOT NULL     DEFAULT 'active',
  created_at            TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meta_connections (
  id                  CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  tenant_id           CHAR(21)     NOT NULL,
  meta_app_id         CHAR(21)     NOT NULL,
  wa_business_id      VARCHAR      NOT NULL     UNIQUE,
  wa_phone_number_id  VARCHAR      NOT NULL     UNIQUE,
  display_number      VARCHAR          NULL,
  access_token        TEXT             NULL,
  token_expires_at    TIMESTAMPTZ      NULL,
  status              status_enum  NOT NULL     DEFAULT 'active',
  created_at          TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

-- WhatsApp chat

CREATE TABLE wa_conversations (
  id            CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  tenant_id     CHAR(21)     NOT NULL,
  full_name     VARCHAR      NOT NULL,
  phone_number  VARCHAR      NOT NULL,
  last_read_id  CHAR(21)         NULL,
  created_at    TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tenant_id, phone_number)
);

CREATE TABLE wa_chats (
  id            CHAR(21)              PRIMARY KEY  DEFAULT nanoid(),
  conv_id       CHAR(21)              NOT NULL,
  wam_id        VARCHAR               NOT NULL     UNIQUE,
  direction     wac_direction_enum    NOT NULL,
  sender_type   wac_sender_type_enum  NOT NULL,
  agent_id      CHAR(21)                  NULL,
  reply_to_id   CHAR(21)                  NULL,
  type          wac_type_enum         NOT NULL,
  message       VARCHAR               NOT NULL,
  attachment    JSON                      NULL,
  status        wac_status_enum           NULL,
  sent_at       TIMESTAMPTZ               NULL,
  delivered_at  TIMESTAMPTZ               NULL,
  read_at       TIMESTAMPTZ               NULL,
  failed_at     TIMESTAMPTZ               NULL,
  created_at    TIMESTAMPTZ           NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMPTZ           NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wa_webhook_events (
  id            CHAR(21)         PRIMARY KEY  DEFAULT nanoid(),
  app_id        VARCHAR          NOT NULL,
  payload       JSONB            NOT NULL,
  status        wwe_status_enum  NOT NULL     DEFAULT 'pending',
  attempts      SMALLINT         NOT NULL     DEFAULT 0,
  error         TEXT                 NULL,
  received_at   TIMESTAMPTZ      NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  claimed_at    TIMESTAMPTZ          NULL,
  processed_at  TIMESTAMPTZ          NULL
);

-- WhatsApp leads

CREATE TABLE wa_lead_stages (
  id           CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  tenant_id    CHAR(21)     NOT NULL,
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

CREATE TABLE wa_leads (
  conv_id                 CHAR(21)      PRIMARY KEY,
  stage_id                CHAR(21)          NULL,
  handler_id              UUID              NULL,
  mode                    wa_mode_enum  NOT NULL     DEFAULT 'human',
  is_internal             BOOLEAN       NOT NULL     DEFAULT false,
  brand_name              VARCHAR           NULL,
  project_value           BIGINT            NULL,
  winning_rate            SMALLINT      NOT NULL     DEFAULT 0,
  note                    VARCHAR           NULL,
  evaluated_last_chat_id  CHAR(21)          NULL,
  created_at              TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at              TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP
);

-- Agent balasan WhatsApp

CREATE TABLE llm_models (
  id            CHAR(21)      PRIMARY KEY  DEFAULT nanoid(),
  provider      VARCHAR(20)   NOT NULL,
  api_model     VARCHAR(100)  NOT NULL,
  display_name  VARCHAR(100)  NOT NULL,
  created_at    TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (provider, api_model),
  CHECK (provider IN ('openai', 'deepseek'))
);

CREATE TABLE agents (
  id                   CHAR(21)      PRIMARY KEY  DEFAULT nanoid(),
  tenant_id            CHAR(21)      NOT NULL,
  model_id             CHAR(21)      NOT NULL,
  name                 VARCHAR(100)  NOT NULL,
  system_prompt        TEXT          NOT NULL,
  transfer_conditions  TEXT          NOT NULL     DEFAULT '',
  config_version       BIGINT        NOT NULL     DEFAULT 1,
  created_at           TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tenant_id, id)
);

CREATE TABLE agent_knowledge_sources (
  id          CHAR(21)      PRIMARY KEY  DEFAULT nanoid(),
  agent_id    CHAR(21)      NOT NULL,
  title       VARCHAR(200)  NOT NULL,
  kind        VARCHAR(16)   NOT NULL,
  source_uri  TEXT              NULL,
  content     TEXT              NULL,
  status      status_enum   NOT NULL     DEFAULT 'inactive',
  created_at  TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  CHECK (kind IN ('text', 'url', 'file'))
);

CREATE TABLE agent_reply_jobs (
  conv_id                 CHAR(21)      PRIMARY KEY,
  latest_inbound_chat_id  CHAR(21)      NOT NULL,
  wa_phone_number_id      VARCHAR       NOT NULL,
  generation              BIGINT        NOT NULL     DEFAULT 1,
  claimed_generation      BIGINT            NULL,
  due_at                  TIMESTAMPTZ   NOT NULL,
  status                  VARCHAR(16)   NOT NULL     DEFAULT 'pending',
  attempts                SMALLINT      NOT NULL     DEFAULT 0,
  claimed_at              TIMESTAMPTZ       NULL,
  error                   TEXT              NULL,
  created_at              TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at              TIMESTAMPTZ   NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  CHECK (status IN ('pending', 'processing', 'sending', 'idle', 'failed', 'send_unknown')),
  CHECK (attempts >= 0)
);

----------------
-- References --
----------------

-- User data

ALTER TABLE tokens
  ADD FOREIGN KEY (user_id) REFERENCES users (id);

ALTER TABLE users_access
  ADD FOREIGN KEY (user_id)   REFERENCES users (id),
  ADD FOREIGN KEY (tenant_id) REFERENCES tenants (id);

-- Meta WhatsApp connections

ALTER TABLE meta_connections
  ADD FOREIGN KEY (tenant_id)   REFERENCES tenants (id),
  ADD FOREIGN KEY (meta_app_id) REFERENCES meta_apps (id);

-- WhatsApp chat

ALTER TABLE wa_conversations
  ADD FOREIGN KEY (tenant_id)    REFERENCES tenants (id),
  ADD FOREIGN KEY (last_read_id) REFERENCES wa_chats (id);

ALTER TABLE wa_chats
  ADD FOREIGN KEY (conv_id)     REFERENCES wa_conversations (id),
  ADD FOREIGN KEY (reply_to_id) REFERENCES wa_chats (id),
  ADD FOREIGN KEY (agent_id)    REFERENCES agents (id);

-- WhatsApp leads

ALTER TABLE wa_lead_stages
  ADD FOREIGN KEY (tenant_id) REFERENCES tenants (id);

ALTER TABLE wa_leads
  ADD FOREIGN KEY (conv_id)                REFERENCES wa_conversations (id),
  ADD FOREIGN KEY (stage_id)               REFERENCES wa_lead_stages (id),
  ADD FOREIGN KEY (handler_id)             REFERENCES users (id),
  ADD FOREIGN KEY (evaluated_last_chat_id) REFERENCES wa_chats (id);

-- Agent balasan WhatsApp

ALTER TABLE agents
  ADD FOREIGN KEY (tenant_id) REFERENCES tenants (id),
  ADD FOREIGN KEY (model_id)  REFERENCES llm_models (id);

ALTER TABLE tenants
  ADD CONSTRAINT tenants_active_agent_same_tenant_fk
  FOREIGN KEY (id, active_agent_id) REFERENCES agents (tenant_id, id);

ALTER TABLE agent_knowledge_sources
  ADD FOREIGN KEY (agent_id) REFERENCES agents (id);

ALTER TABLE agent_reply_jobs
  ADD FOREIGN KEY (conv_id)                REFERENCES wa_conversations (id),
  ADD FOREIGN KEY (latest_inbound_chat_id) REFERENCES wa_chats (id);

-------------
-- Indexes --
-------------

-- User data

CREATE INDEX tokens_user_id_idx          ON tokens (user_id);
CREATE INDEX users_access_user_id_idx    ON users_access (user_id);
CREATE INDEX users_access_tenant_id_idx  ON users_access (tenant_id);

-- Meta WhatsApp connections

CREATE INDEX meta_connections_tenant_id_idx    ON meta_connections (tenant_id);
CREATE INDEX meta_connections_meta_app_id_idx  ON meta_connections (meta_app_id);

-- WhatsApp chat

CREATE INDEX wa_conversations_tenant_id_idx   ON wa_conversations (tenant_id);
CREATE INDEX wa_conversations_full_name_trgm_idx  ON wa_conversations USING gin (full_name gin_trgm_ops);
CREATE INDEX wa_chats_message_trgm_idx           ON wa_chats USING gin (message gin_trgm_ops);
CREATE INDEX wa_chats_conv_id_created_at_idx  ON wa_chats (conv_id, created_at DESC);
CREATE INDEX wa_chats_attachment_sha256_idx   ON wa_chats ((attachment ->> 'sha256'))
  WHERE (attachment ->> 'storage_url') IS NOT NULL;

-- WhatsApp leads

CREATE INDEX wa_leads_stage_id_idx         ON wa_leads (stage_id);
CREATE INDEX wa_leads_brand_name_trgm_idx  ON wa_leads USING gin (brand_name gin_trgm_ops);

-- Webhook Meta

CREATE INDEX wa_webhook_events_status_idx       ON wa_webhook_events (status, received_at);
CREATE INDEX wa_webhook_events_received_at_idx  ON wa_webhook_events (received_at DESC);

-- Agent balasan WhatsApp

CREATE INDEX agents_tenant_id_idx ON agents (tenant_id);
CREATE INDEX agents_model_id_idx ON agents (model_id);
CREATE INDEX agent_knowledge_sources_agent_status_idx ON agent_knowledge_sources (agent_id, status);
CREATE INDEX agent_reply_jobs_due_idx ON agent_reply_jobs (due_at) WHERE status = 'pending';
CREATE INDEX agent_reply_jobs_claimed_idx ON agent_reply_jobs (claimed_at)
  WHERE status = 'processing';
CREATE INDEX wa_chats_agent_id_idx ON wa_chats (agent_id) WHERE agent_id IS NOT NULL;

ALTER TABLE llm_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_reply_jobs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON llm_models, agents, agent_knowledge_sources, agent_reply_jobs
  FROM anon, authenticated;

-----------------
-- Seed models --
-----------------

INSERT INTO llm_models (provider, api_model, display_name) VALUES
  ('openai', 'gpt-4.1-mini', 'GPT-4.1 mini'),
  ('openai', 'gpt-4.1', 'GPT-4.1');
