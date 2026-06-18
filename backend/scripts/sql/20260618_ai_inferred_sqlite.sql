-- SQLite: 添加 ai_inferred 字段到 ingredients 和 recipe_ingredients 表
-- 对应 Alembic: 20260618_0001_add_ai_inferred_fields.py

ALTER TABLE ingredients ADD COLUMN ai_inferred INTEGER NOT NULL DEFAULT 0;
ALTER TABLE recipe_ingredients ADD COLUMN ai_inferred INTEGER NOT NULL DEFAULT 0;
