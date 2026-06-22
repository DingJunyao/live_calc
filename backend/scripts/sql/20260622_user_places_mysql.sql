-- 用户常用地点表（家/公司等），供商家管理地图默认聚焦；取代遗留的 favorite_merchants
-- 引擎：MySQL

DROP TABLE IF EXISTS favorite_merchants;

CREATE TABLE user_places (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    kind VARCHAR(20) NOT NULL DEFAULT 'custom',
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    address VARCHAR(255),
    is_default BOOLEAN NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    view_radius_km DECIMAL(10, 2) NOT NULL DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id),
    INDEX ix_user_places_user_id (user_id),
    CONSTRAINT fk_user_places_user_id FOREIGN KEY (user_id) REFERENCES users (id)
);
