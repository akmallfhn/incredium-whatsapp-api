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

-- Enumeration for the wa_conversations table (wa_*)

CREATE TYPE wa_lead_status_enum AS ENUM (
  'cold',
  'qualified',
  'rate_card_sent',
  'negotiation',
  'closed'
);

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
  'admin'
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
  id          CHAR(21)     PRIMARY KEY  DEFAULT nanoid(),
  name        VARCHAR      NOT NULL,
  slug        VARCHAR      NOT NULL     UNIQUE,
  status      status_enum  NOT NULL     DEFAULT 'active',
  created_at  TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMPTZ  NOT NULL     DEFAULT CURRENT_TIMESTAMP
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
  id             CHAR(21)             PRIMARY KEY  DEFAULT nanoid(),
  tenant_id      CHAR(21)             NOT NULL,
  full_name      VARCHAR              NOT NULL,
  phone_number   VARCHAR              NOT NULL,
  brand_name     VARCHAR                  NULL,
  handler_id     UUID                     NULL,
  lead_status    wa_lead_status_enum  NOT NULL     DEFAULT 'cold',
  project_value  BIGINT                   NULL,
  winning_rate   SMALLINT             NOT NULL     DEFAULT 0,
  mode           wa_mode_enum         NOT NULL     DEFAULT 'human',
  note           VARCHAR                  NULL,
  is_internal    BOOLEAN              NOT NULL     DEFAULT false,
  last_read_id   CHAR(21)                 NULL,
  created_at     TIMESTAMPTZ          NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMPTZ          NOT NULL     DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tenant_id, phone_number)
);

CREATE TABLE wa_chats (
  id            CHAR(21)              PRIMARY KEY  DEFAULT nanoid(),
  conv_id       CHAR(21)              NOT NULL,
  wam_id        VARCHAR               NOT NULL     UNIQUE,
  direction     wac_direction_enum    NOT NULL,
  sender_type   wac_sender_type_enum  NOT NULL,
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

----------------
-- References --
----------------

-- User data

ALTER TABLE tokens
  ADD FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;

ALTER TABLE users_access
  ADD FOREIGN KEY (user_id)   REFERENCES users (id)   ON DELETE CASCADE,
  ADD FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE;

-- Meta WhatsApp connections

ALTER TABLE meta_connections
  ADD FOREIGN KEY (tenant_id)   REFERENCES tenants (id),
  ADD FOREIGN KEY (meta_app_id) REFERENCES meta_apps (id);

-- WhatsApp chat

ALTER TABLE wa_conversations
  ADD FOREIGN KEY (tenant_id)    REFERENCES tenants (id),
  ADD FOREIGN KEY (handler_id)   REFERENCES users (id),
  ADD FOREIGN KEY (last_read_id) REFERENCES wa_chats (id);

ALTER TABLE wa_chats
  ADD FOREIGN KEY (conv_id)     REFERENCES wa_conversations (id),
  ADD FOREIGN KEY (reply_to_id) REFERENCES wa_chats (id);

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

CREATE INDEX wa_conversations_tenant_id_idx  ON wa_conversations (tenant_id);
CREATE INDEX wa_chats_conv_id_idx            ON wa_chats (conv_id);

-- Webhook Meta

CREATE INDEX wa_webhook_events_status_idx       ON wa_webhook_events (status, received_at);
CREATE INDEX wa_webhook_events_received_at_idx  ON wa_webhook_events (received_at DESC);
