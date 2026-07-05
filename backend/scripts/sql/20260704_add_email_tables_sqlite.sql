-- SMTP 发送配置与邮件模板表（SQLite）
-- smtp_config：单行表（固定 id=1），存储 SMTP 发信配置
-- email_templates：邮件模板，key 为唯一标识，body_html 支持 ${变量} 模板语法

CREATE TABLE IF NOT EXISTS smtp_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls INTEGER NOT NULL DEFAULT 1,
    use_ssl INTEGER NOT NULL DEFAULT 0,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO email_templates (key, name, subject, body_html, description) VALUES
('proposal_submitted', '新提议通知（管理员）',
 '[LiveCalc] 新提议 ${proposal_id}',
 '<h2>新变更提议</h2><p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '用户提交变更提议时通知所有管理员'),
('proposal_approved', '提议通过通知（发起者）',
 '[LiveCalc] 提议 ${proposal_id} 已通过',
 '<h2>提议已通过</h2><p>您的变更提议已通过审核并生效。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '提议审核通过时通知发起者'),
('proposal_rejected', '提议驳回通知（发起者）',
 '[LiveCalc] 提议 ${proposal_id} 未通过',
 '<h2>提议未通过</h2><p>您的变更提议未通过审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table><p>审核备注：${review_note}</p>',
 '提议审核驳回时通知发起者');
