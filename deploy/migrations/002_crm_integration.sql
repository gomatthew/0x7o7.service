-- migration_id: 002_crm_integration
-- Incremental and idempotent CRM schema migration. This file must be applied to crm_data only.
-- It never references, creates, alters, or writes market_source.

CREATE TABLE IF NOT EXISTS crm_schema_migrations (
  migration_id VARCHAR(96) PRIMARY KEY,
  applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP PROCEDURE IF EXISTS crm_add_column_if_missing;
DELIMITER //
CREATE PROCEDURE crm_add_column_if_missing(
  IN target_table VARCHAR(64),
  IN target_column VARCHAR(64),
  IN column_definition TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = target_table
      AND COLUMN_NAME = target_column
  ) THEN
    SET @crm_column_sql = CONCAT(
      'ALTER TABLE `', REPLACE(target_table, '`', '``'),
      '` ADD COLUMN `', REPLACE(target_column, '`', '``'), '` ', column_definition
    );
    PREPARE crm_column_statement FROM @crm_column_sql;
    EXECUTE crm_column_statement;
    DEALLOCATE PREPARE crm_column_statement;
  END IF;
END//
DELIMITER ;

CALL crm_add_column_if_missing('crm_deals', 'market_opportunity_id', 'VARCHAR(40) NULL AFTER `contact_id`');

CREATE TABLE IF NOT EXISTS crm_approval_requests (
  id VARCHAR(48) PRIMARY KEY,
  owner_user_id VARCHAR(64) NOT NULL,
  request_type VARCHAR(32) NOT NULL,
  subject VARCHAR(300) NOT NULL,
  subject_type VARCHAR(32) NULL,
  subject_id VARCHAR(96) NULL,
  market_opportunity_id VARCHAR(40) NULL,
  company_id INT NULL,
  contact_id INT NULL,
  title VARCHAR(300) NOT NULL,
  recommendation TEXT NOT NULL,
  evidence_json JSON NOT NULL,
  impact VARCHAR(32) NOT NULL,
  effort TEXT NOT NULL,
  risk TEXT NOT NULL,
  constraints_text TEXT NOT NULL,
  action_pack TEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  execution_owner VARCHAR(32) NOT NULL DEFAULT 'user',
  execution_kind VARCHAR(32) NOT NULL DEFAULT 'manual_external',
  requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  decision_note TEXT NULL,
  decided_at DATETIME NULL,
  started_at DATETIME NULL,
  completed_at DATETIME NULL,
  output_refs JSON NULL,
  output_note TEXT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_crm_approval_owner_status (owner_user_id, status, requested_at),
  INDEX ix_crm_approval_market_opportunity (market_opportunity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CALL crm_add_column_if_missing('crm_approval_requests', 'owner_user_id', 'VARCHAR(64) NOT NULL DEFAULT ''6'' AFTER `id`');
CALL crm_add_column_if_missing('crm_approval_requests', 'subject_type', 'VARCHAR(32) NULL AFTER `subject`');
CALL crm_add_column_if_missing('crm_approval_requests', 'subject_id', 'VARCHAR(96) NULL AFTER `subject_type`');
CALL crm_add_column_if_missing('crm_approval_requests', 'market_opportunity_id', 'VARCHAR(40) NULL AFTER `subject_id`');
CALL crm_add_column_if_missing('crm_approval_requests', 'company_id', 'INT NULL AFTER `market_opportunity_id`');
CALL crm_add_column_if_missing('crm_approval_requests', 'contact_id', 'INT NULL AFTER `company_id`');
CALL crm_add_column_if_missing('crm_approval_requests', 'execution_owner', 'VARCHAR(32) NOT NULL DEFAULT ''user'' AFTER `status`');
CALL crm_add_column_if_missing('crm_approval_requests', 'execution_kind', 'VARCHAR(32) NOT NULL DEFAULT ''manual_external'' AFTER `execution_owner`');
CALL crm_add_column_if_missing('crm_approval_requests', 'started_at', 'DATETIME NULL AFTER `decided_at`');
CALL crm_add_column_if_missing('crm_approval_requests', 'completed_at', 'DATETIME NULL AFTER `started_at`');
CALL crm_add_column_if_missing('crm_approval_requests', 'output_refs', 'JSON NULL AFTER `completed_at`');
CALL crm_add_column_if_missing('crm_approval_requests', 'output_note', 'TEXT NULL AFTER `output_refs`');
CALL crm_add_column_if_missing('crm_approval_requests', 'updated_at', 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');

UPDATE crm_approval_requests
SET execution_owner = CASE request_type
    WHEN 'research_focus' THEN 'research_agent'
    WHEN 'create_lead' THEN 'crm_agent'
    WHEN 'demo' THEN 'code_agent'
    ELSE execution_owner END,
    execution_kind = CASE request_type
    WHEN 'research_focus' THEN 'research'
    WHEN 'create_lead' THEN 'lead_qualification'
    WHEN 'demo' THEN 'demo_design'
    ELSE execution_kind END
WHERE execution_owner = 'user' AND execution_kind = 'manual_external'
  AND request_type IN ('research_focus', 'create_lead', 'demo');

CREATE TABLE IF NOT EXISTS crm_execution_tasks (
  task_id VARCHAR(96) PRIMARY KEY,
  approval_id VARCHAR(48) NOT NULL,
  owner_user_id VARCHAR(64) NOT NULL,
  execution_owner VARCHAR(32) NOT NULL,
  execution_kind VARCHAR(32) NOT NULL,
  task_status VARCHAR(24) NOT NULL DEFAULT 'queued',
  title VARCHAR(300) NOT NULL,
  action_pack TEXT NOT NULL,
  output_refs JSON NULL,
  output_note TEXT NULL,
  started_at DATETIME NULL,
  completed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_crm_execution_task_approval (owner_user_id, approval_id),
  INDEX ix_crm_execution_task_queue (owner_user_id, execution_owner, task_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CALL crm_add_column_if_missing('crm_execution_tasks', 'owner_user_id', 'VARCHAR(64) NOT NULL DEFAULT ''6'' AFTER `approval_id`');

INSERT IGNORE INTO crm_execution_tasks
  (task_id, approval_id, owner_user_id, execution_owner, execution_kind, task_status, title, action_pack)
SELECT CONCAT('TASK-', id), id, owner_user_id, execution_owner, execution_kind, 'queued', title, action_pack
FROM crm_approval_requests
WHERE status = 'approved_not_executed'
  AND execution_kind <> 'manual_external';

CREATE TABLE IF NOT EXISTS crm_decision_activities (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  owner_user_id VARCHAR(64) NOT NULL,
  approval_id VARCHAR(48) NULL,
  event_text TEXT NOT NULL,
  event_tone VARCHAR(16) NOT NULL DEFAULT 'system',
  actor VARCHAR(32) NOT NULL DEFAULT 'user',
  event_type VARCHAR(48) NOT NULL DEFAULT 'legacy',
  entity_type VARCHAR(32) NULL,
  entity_id VARCHAR(96) NULL,
  metadata_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_crm_decision_activity_created (owner_user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CALL crm_add_column_if_missing('crm_decision_activities', 'owner_user_id', 'VARCHAR(64) NOT NULL DEFAULT ''6'' AFTER `id`');
CALL crm_add_column_if_missing('crm_decision_activities', 'approval_id', 'VARCHAR(48) NULL AFTER `owner_user_id`');
CALL crm_add_column_if_missing('crm_decision_activities', 'actor', 'VARCHAR(32) NOT NULL DEFAULT ''user'' AFTER `event_tone`');
CALL crm_add_column_if_missing('crm_decision_activities', 'event_type', 'VARCHAR(48) NOT NULL DEFAULT ''legacy'' AFTER `actor`');
CALL crm_add_column_if_missing('crm_decision_activities', 'entity_type', 'VARCHAR(32) NULL AFTER `event_type`');
CALL crm_add_column_if_missing('crm_decision_activities', 'entity_id', 'VARCHAR(96) NULL AFTER `entity_type`');
CALL crm_add_column_if_missing('crm_decision_activities', 'metadata_json', 'JSON NULL AFTER `entity_id`');

CREATE TABLE IF NOT EXISTS crm_interactions (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  contact_id INT NOT NULL,
  draft_id INT NULL,
  channel VARCHAR(32) NOT NULL,
  direction VARCHAR(32) NOT NULL,
  occurred_at DATETIME NOT NULL,
  summary TEXT NOT NULL,
  outcome TEXT NULL,
  next_followup_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  owner_user_id VARCHAR(64) NOT NULL,
  INDEX ix_crm_interaction_contact_time (contact_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS crm_opportunity_links (
  opportunity_id VARCHAR(40) NOT NULL,
  entity_type VARCHAR(32) NOT NULL,
  entity_id VARCHAR(96) NOT NULL,
  relation_type VARCHAR(32) NOT NULL,
  owner_user_id VARCHAR(64) NOT NULL DEFAULT '6',
  market_signal_id VARCHAR(40) NULL,
  market_source_id VARCHAR(40) NULL,
  metadata_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (opportunity_id, entity_type, entity_id, relation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CALL crm_add_column_if_missing('crm_opportunity_links', 'owner_user_id', 'VARCHAR(64) NOT NULL DEFAULT ''6'' AFTER `relation_type`');
CALL crm_add_column_if_missing('crm_opportunity_links', 'market_signal_id', 'VARCHAR(40) NULL AFTER `owner_user_id`');
CALL crm_add_column_if_missing('crm_opportunity_links', 'market_source_id', 'VARCHAR(40) NULL AFTER `market_signal_id`');

CREATE TABLE IF NOT EXISTS crm_legacy_imports (
  source_key VARCHAR(160) PRIMARY KEY,
  source_hash CHAR(64) NOT NULL,
  imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS crm_legacy_record_maps (
  source_system VARCHAR(64) NOT NULL,
  entity_type VARCHAR(32) NOT NULL,
  source_record_id VARCHAR(96) NOT NULL,
  target_record_id VARCHAR(96) NOT NULL,
  source_hash CHAR(64) NOT NULL,
  imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (source_system, entity_type, source_record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT IGNORE INTO crm_schema_migrations (migration_id)
VALUES ('002_crm_integration');

DROP PROCEDURE IF EXISTS crm_add_column_if_missing;
