-- 通用变更提议表（MySQL）
-- 治理共享数据的写入：普通用户提交 → 按审核策略（auto_approve/auto_review/manual）流转

CREATE TABLE IF NOT EXISTS change_proposals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(32) NOT NULL,
    entity_id INT,
    action VARCHAR(16) NOT NULL,
    payload JSON NOT NULL,
    snapshot JSON,
    revert_payload JSON,
    review_policy VARCHAR(16) NOT NULL DEFAULT 'manual',
    risk_level VARCHAR(8) NOT NULL DEFAULT 'mid',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    proposer_id INT NOT NULL,
    reviewer_id INT,
    review_note TEXT,
    revertable_until DATETIME,
    applied_at DATETIME,
    reviewed_at DATETIME,
    reverted_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    updated_by INT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (proposer_id) REFERENCES users(id),
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_change_proposals_entity_type ON change_proposals(entity_type);
CREATE INDEX ix_change_proposals_entity_id ON change_proposals(entity_id);
CREATE INDEX ix_change_proposals_status ON change_proposals(status);
CREATE INDEX ix_change_proposals_proposer_id ON change_proposals(proposer_id);
