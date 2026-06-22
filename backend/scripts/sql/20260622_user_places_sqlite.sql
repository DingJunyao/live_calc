-- 用户常用地点表（家/公司等），供商家管理地图默认聚焦；取代遗留的 favorite_merchants
-- 引擎：SQLite

DROP TABLE IF EXISTS favorite_merchants;

CREATE TABLE user_places (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    kind VARCHAR(20) NOT NULL DEFAULT 'custom',
    latitude NUMERIC(10, 7) NOT NULL,
    longitude NUMERIC(10, 7) NOT NULL,
    address VARCHAR(255),
    is_default BOOLEAN NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    view_radius_km NUMERIC(10, 2) NOT NULL DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX ix_user_places_id ON user_places (id);
CREATE INDEX ix_user_places_user_id ON user_places (user_id);
