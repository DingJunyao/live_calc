-- ============================================================
-- 单位管理系统迁移脚本
-- 版本: fa24d2d1491a
-- 日期: 2026-05-21
-- 说明: 添加 unit_system/default_estimate 列，创建 entity_unit_overrides 和 entity_densities 表
-- ============================================================


-- ============================================================
-- 一、SQLite 版本
-- ============================================================

-- 1. units 表新增列
ALTER TABLE units ADD COLUMN unit_system VARCHAR(20);
ALTER TABLE units ADD COLUMN default_estimate NUMERIC(10, 3);

-- 2. 数据迁移：设置现有单位的 unit_system
UPDATE units SET unit_system = 'metric' WHERE abbreviation IN ('g', 'kg', 'mg', 'L', 'ml', 'mL', 'm', 'cm', 'mm');
UPDATE units SET unit_system = 'market' WHERE abbreviation IN ('斤', '两', '钱', '杯', '汤匙', '茶匙');
UPDATE units SET unit_system = 'imperial' WHERE abbreviation IN ('lb', 'oz', 'cup', 'fl oz', 'ft', 'in');
UPDATE units SET unit_system = 'count' WHERE unit_type = 'count';

-- 3. 创建 entity_unit_overrides 表
CREATE TABLE entity_unit_overrides (
    id INTEGER NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    unit_name VARCHAR(50) NOT NULL,
    base_unit_id INTEGER,
    conversion_factor NUMERIC(15, 10),
    weight_per_unit NUMERIC(10, 3),
    weight_unit_id INTEGER,
    is_default BOOLEAN,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_entity_unit UNIQUE (entity_type, entity_id, unit_name),
    FOREIGN KEY(base_unit_id) REFERENCES units (id),
    FOREIGN KEY(weight_unit_id) REFERENCES units (id)
);
CREATE INDEX ix_entity_unit_overrides_id ON entity_unit_overrides (id);

-- 4. 创建 entity_densities 表
CREATE TABLE entity_densities (
    id INTEGER NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    density NUMERIC(10, 6) NOT NULL,
    temperature NUMERIC(5, 2),
    condition VARCHAR(100),
    source VARCHAR(200),
    confidence NUMERIC(3, 2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_entity_density UNIQUE (entity_type, entity_id, condition)
);
CREATE INDEX ix_entity_densities_id ON entity_densities (id);


-- ============================================================
-- 二、MySQL 版本
-- ============================================================

-- 1. units 表新增列
ALTER TABLE units ADD COLUMN unit_system VARCHAR(20) DEFAULT NULL;
ALTER TABLE units ADD COLUMN default_estimate DECIMAL(10, 3) DEFAULT NULL;

-- 2. 数据迁移：设置现有单位的 unit_system
UPDATE units SET unit_system = 'metric' WHERE abbreviation IN ('g', 'kg', 'mg', 'L', 'ml', 'mL', 'm', 'cm', 'mm');
UPDATE units SET unit_system = 'market' WHERE abbreviation IN ('斤', '两', '钱', '杯', '汤匙', '茶匙');
UPDATE units SET unit_system = 'imperial' WHERE abbreviation IN ('lb', 'oz', 'cup', 'fl oz', 'ft', 'in');
UPDATE units SET unit_system = 'count' WHERE unit_type = 'count';

-- 3. 创建 entity_unit_overrides 表
CREATE TABLE entity_unit_overrides (
    id INT NOT NULL AUTO_INCREMENT,
    entity_type VARCHAR(20) NOT NULL COMMENT 'ingredient 或 product',
    entity_id INT NOT NULL,
    unit_name VARCHAR(50) NOT NULL COMMENT '如 "盒(12个)"、"根"',
    base_unit_id INT DEFAULT NULL COMMENT '指向基础单位（如 "个"）',
    conversion_factor DECIMAL(15, 10) DEFAULT NULL COMMENT '换算系数',
    weight_per_unit DECIMAL(10, 3) DEFAULT NULL COMMENT '单位重量（g）',
    weight_unit_id INT DEFAULT NULL COMMENT '指向质量单位',
    is_default TINYINT(1) DEFAULT 0 COMMENT '是否为默认单位',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_entity_unit (entity_type, entity_id, unit_name),
    KEY ix_entity_unit_overrides_id (id),
    CONSTRAINT fk_entity_unit_base FOREIGN KEY (base_unit_id) REFERENCES units (id),
    CONSTRAINT fk_entity_unit_weight FOREIGN KEY (weight_unit_id) REFERENCES units (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实体单位覆盖表';

-- 4. 创建 entity_densities 表
CREATE TABLE entity_densities (
    id INT NOT NULL AUTO_INCREMENT,
    entity_type VARCHAR(20) NOT NULL COMMENT 'ingredient 或 product',
    entity_id INT NOT NULL,
    density DECIMAL(10, 6) NOT NULL COMMENT '密度（kg/m³）',
    temperature DECIMAL(5, 2) DEFAULT NULL COMMENT '参考温度（℃）',
    condition VARCHAR(100) DEFAULT NULL COMMENT '状态描述',
    source VARCHAR(200) DEFAULT NULL COMMENT '数据来源',
    confidence DECIMAL(3, 2) DEFAULT 1.00 COMMENT '数据可信度',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_entity_density (entity_type, entity_id, `condition`),
    KEY ix_entity_densities_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实体密度表';


-- ============================================================
-- 三、PostgreSQL 版本（不带 PostGIS）
-- ============================================================

-- 1. units 表新增列
ALTER TABLE units ADD COLUMN unit_system VARCHAR(20);
ALTER TABLE units ADD COLUMN default_estimate NUMERIC(10, 3);

-- 2. 数据迁移：设置现有单位的 unit_system
UPDATE units SET unit_system = 'metric' WHERE abbreviation IN ('g', 'kg', 'mg', 'L', 'ml', 'mL', 'm', 'cm', 'mm');
UPDATE units SET unit_system = 'market' WHERE abbreviation IN ('斤', '两', '钱', '杯', '汤匙', '茶匙');
UPDATE units SET unit_system = 'imperial' WHERE abbreviation IN ('lb', 'oz', 'cup', 'fl oz', 'ft', 'in');
UPDATE units SET unit_system = 'count' WHERE unit_type = 'count';

-- 3. 创建 entity_unit_overrides 表
CREATE TABLE entity_unit_overrides (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    unit_name VARCHAR(50) NOT NULL,
    base_unit_id INTEGER REFERENCES units(id),
    conversion_factor NUMERIC(15, 10),
    weight_per_unit NUMERIC(10, 3),
    weight_unit_id INTEGER REFERENCES units(id),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_entity_unit UNIQUE (entity_type, entity_id, unit_name)
);
CREATE INDEX ix_entity_unit_overrides_id ON entity_unit_overrides (id);

-- 4. 创建 entity_densities 表
CREATE TABLE entity_densities (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    density NUMERIC(10, 6) NOT NULL,
    temperature NUMERIC(5, 2),
    condition VARCHAR(100),
    source VARCHAR(200),
    confidence NUMERIC(3, 2) DEFAULT 1.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_entity_density UNIQUE (entity_type, entity_id, condition)
);
CREATE INDEX ix_entity_densities_id ON entity_densities (id);


-- ============================================================
-- 回滚脚本（所有引擎通用调整）
-- ============================================================

-- SQLite 回滚
-- DROP TABLE IF EXISTS entity_densities;
-- DROP TABLE IF EXISTS entity_unit_overrides;
-- ALTER TABLE units DROP COLUMN default_estimate;  -- SQLite 不支持 DROP COLUMN（3.35.0 之前）
-- ALTER TABLE units DROP COLUMN unit_system;

-- MySQL 回滚
-- DROP TABLE IF EXISTS entity_densities;
-- DROP TABLE IF EXISTS entity_unit_overrides;
-- ALTER TABLE units DROP COLUMN default_estimate;
-- ALTER TABLE units DROP COLUMN unit_system;

-- PostgreSQL 回滚
-- DROP TABLE IF EXISTS entity_densities;
-- DROP TABLE IF EXISTS entity_unit_overrides;
-- ALTER TABLE units DROP COLUMN default_estimate;
-- ALTER TABLE units DROP COLUMN unit_system;
