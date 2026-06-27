-- 通用变更提议表（PostgreSQL，无 PostGIS）
-- 治理共享数据的写入：普通用户提交 → 按审核策略（auto_approve/auto_review/manual）流转

CREATE TABLE IF NOT EXISTS change_proposals (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(32) NOT NULL,
    entity_id INT,
    action VARCHAR(16) NOT NULL,
    payload JSONB NOT NULL,
    snapshot JSONB,
    revert_payload JSONB,
    review_policy VARCHAR(16) NOT NULL DEFAULT 'manual',
    risk_level VARCHAR(8) NOT NULL DEFAULT 'mid',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    proposer_id INT NOT NULL REFERENCES users(id),
    reviewer_id INT REFERENCES users(id),
    review_note TEXT,
    revertable_until TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    reverted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_type ON change_proposals(entity_type);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_id ON change_proposals(entity_id);
CREATE INDEX IF NOT EXISTS ix_change_proposals_status ON change_proposals(status);
CREATE INDEX IF NOT EXISTS ix_change_proposals_proposer_id ON change_proposals(proposer_id);
