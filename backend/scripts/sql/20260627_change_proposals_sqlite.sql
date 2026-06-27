-- 通用变更提议表（SQLite）
-- 治理共享数据的写入：普通用户提交 → 按审核策略（auto_approve/auto_review/manual）流转

CREATE TABLE IF NOT EXISTS change_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    snapshot TEXT,
    revert_payload TEXT,
    review_policy TEXT NOT NULL DEFAULT 'manual',
    risk_level TEXT NOT NULL DEFAULT 'mid',
    status TEXT NOT NULL DEFAULT 'pending',
    proposer_id INTEGER NOT NULL REFERENCES users(id),
    reviewer_id INTEGER REFERENCES users(id),
    review_note TEXT,
    revertable_until TEXT,
    applied_at TEXT,
    reviewed_at TEXT,
    reverted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    is_active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_type ON change_proposals(entity_type);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_id ON change_proposals(entity_id);
CREATE INDEX IF NOT EXISTS ix_change_proposals_status ON change_proposals(status);
CREATE INDEX IF NOT EXISTS ix_change_proposals_proposer_id ON change_proposals(proposer_id);
