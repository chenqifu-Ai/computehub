-- AI智能招商平台 - 数据库初始化脚本
-- 版本: v1.0
-- 日期: 2026-05-09

-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_zhaoshang 
  DEFAULT CHARACTER SET utf8mb4 
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE ai_zhaoshang;

-- ============================================================
-- 1. 用户与权限
-- ============================================================

-- 角色表
CREATE TABLE sys_role (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE COMMENT '角色代码',
    name VARCHAR(100) NOT NULL COMMENT '角色名称',
    description VARCHAR(255) COMMENT '角色描述',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '0=禁用 1=启用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='角色表';

-- 权限表
CREATE TABLE sys_permission (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE COMMENT '权限代码',
    name VARCHAR(100) NOT NULL COMMENT '权限名称',
    type VARCHAR(20) NOT NULL DEFAULT 'menu' COMMENT 'menu|button|api',
    parent_id BIGINT UNSIGNED DEFAULT NULL,
    path VARCHAR(255) COMMENT '路由路径',
    sort_order INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB COMMENT='权限表';

-- 角色权限关联
CREATE TABLE sys_role_permission (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_id BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    UNIQUE KEY uk_role_perm (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES sys_role(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES sys_permission(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='角色权限关联表';

-- 用户表
CREATE TABLE sys_user (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt哈希密码',
    real_name VARCHAR(50) NOT NULL COMMENT '真实姓名',
    phone VARCHAR(20) COMMENT '手机号',
    email VARCHAR(100) COMMENT '邮箱',
    avatar_url VARCHAR(500) COMMENT '头像URL',
    role_id BIGINT UNSIGNED NOT NULL,
    status TINYINT NOT NULL DEFAULT 1 COMMENT '0=禁用 1=正常',
    last_login_at DATETIME COMMENT '最后登录时间',
    last_login_ip VARCHAR(45) COMMENT '最后登录IP',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES sys_role(id),
    INDEX idx_phone (phone),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='用户表';

-- ============================================================
-- 2. 设备管理
-- ============================================================

CREATE TABLE sys_device (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL UNIQUE COMMENT '设备唯一标识',
    device_name VARCHAR(100) COMMENT '设备名称',
    device_type VARCHAR(20) NOT NULL DEFAULT 'box' COMMENT '类型',
    region VARCHAR(50) COMMENT '所属区域',
    city VARCHAR(50) COMMENT '所在城市',
    address VARCHAR(255) COMMENT '安装地址',
    online_status TINYINT NOT NULL DEFAULT 0 COMMENT '0=离线 1=在线',
    last_heartbeat_at DATETIME COMMENT '最后心跳时间',
    current_version VARCHAR(20) COMMENT '当前版本',
    target_version VARCHAR(20) COMMENT '目标版本',
    ip_address VARCHAR(45) COMMENT '最后IP',
    installed_at DATETIME COMMENT '安装时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_region (region),
    INDEX idx_online (online_status),
    INDEX idx_heartbeat (last_heartbeat_at)
) ENGINE=InnoDB COMMENT='设备表';

-- ============================================================
-- 3. 招商全案内容
-- ============================================================

CREATE TABLE biz_brand (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '品牌名称',
    slogan VARCHAR(200) COMMENT '品牌口号',
    logo_url VARCHAR(500) COMMENT 'Logo地址',
    intro TEXT COMMENT '品牌介绍',
    honor_list JSON COMMENT '荣誉资质列表',
    sort_order INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='品牌表';

CREATE TABLE biz_product (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    brand_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL COMMENT '产品名称',
    description TEXT COMMENT '产品描述',
    images JSON COMMENT '产品图片列表',
    specs JSON COMMENT '产品规格参数',
    price_range VARCHAR(100) COMMENT '价格区间',
    highlight TEXT COMMENT '核心卖点',
    sort_order INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES biz_brand(id),
    INDEX idx_brand (brand_id),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='产品表';

CREATE TABLE biz_model (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '模式名称',
    type VARCHAR(50) NOT NULL COMMENT '类型: franchise/partner/distributor',
    description TEXT COMMENT '模式描述',
    conditions JSON COMMENT '合作条件',
    benefits JSON COMMENT '合作权益',
    sort_order INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (type)
) ENGINE=InnoDB COMMENT='合作模式表';

CREATE TABLE biz_investment (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL COMMENT '投资项标题',
    item_name VARCHAR(100) NOT NULL COMMENT '项目名称',
    amount DECIMAL(10,2) NOT NULL COMMENT '金额(元)',
    description TEXT COMMENT '说明',
    category VARCHAR(50) COMMENT '分类',
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category)
) ENGINE=InnoDB COMMENT='投资明细表';

CREATE TABLE biz_support (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL COMMENT '扶持标题',
    category VARCHAR(50) NOT NULL COMMENT '分类: 选址/装修/培训/营销/运营',
    description TEXT NOT NULL COMMENT '扶持内容',
    images JSON COMMENT '配图',
    sort_order INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='扶持政策表';

CREATE TABLE biz_case (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    franchisee_name VARCHAR(100) NOT NULL COMMENT '加盟商姓名',
    city VARCHAR(50) NOT NULL COMMENT '城市',
    store_type VARCHAR(50) COMMENT '门店类型',
    investment_amount DECIMAL(10,2) COMMENT '投资金额',
    return_months INT COMMENT '回本周期(月)',
    content TEXT NOT NULL COMMENT '案例内容',
    images JSON COMMENT '图片',
    video_url VARCHAR(500) COMMENT '视频链接',
    sort_order INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='案例表';

-- ============================================================
-- 4. 问答库
-- ============================================================

CREATE TABLE biz_qa (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL COMMENT '分类',
    question VARCHAR(500) NOT NULL COMMENT '问题',
    answer TEXT NOT NULL COMMENT '标准答案',
    keywords JSON COMMENT '关键词',
    audio_url VARCHAR(500) COMMENT '语音答案地址',
    use_count INT NOT NULL DEFAULT 0 COMMENT '使用次数',
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='问答库表';

-- ============================================================
-- 5. 内容版本管理
-- ============================================================

CREATE TABLE biz_content_version (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE COMMENT '版本号',
    content_type VARCHAR(50) NOT NULL COMMENT '内容类型',
    changelog TEXT COMMENT '更新说明',
    is_major_release TINYINT NOT NULL DEFAULT 0 COMMENT '是否大版本',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0=草稿 1=已发布 2=已回滚',
    created_by BIGINT UNSIGNED NOT NULL,
    published_at DATETIME COMMENT '发布时间',
    rollback_at DATETIME COMMENT '回滚时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES sys_user(id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='内容版本表';

CREATE TABLE sys_device_version (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL COMMENT '设备ID',
    content_version VARCHAR(20) NOT NULL COMMENT '内容版本',
    app_version VARCHAR(20) NOT NULL COMMENT 'App版本',
    update_status TINYINT NOT NULL DEFAULT 0 COMMENT '0=未更新 1=更新中 2=已更新',
    updated_at DATETIME COMMENT '更新时间',
    updated_by VARCHAR(50) COMMENT '更新方式: auto/manual',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_device_ver (device_id, content_version),
    INDEX idx_update_status (update_status)
) ENGINE=InnoDB COMMENT='设备版本绑定表';

-- ============================================================
-- 6. 数据统计
-- ============================================================

CREATE TABLE stat_query_log (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL COMMENT '设备ID',
    query_text VARCHAR(500) NOT NULL COMMENT '查询文本',
    query_result TEXT COMMENT '查询结果摘要',
    duration_ms INT COMMENT '响应耗时(ms)',
    slide_id BIGINT UNSIGNED COMMENT '当前页面ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device (device_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='查询日志表';

CREATE TABLE stat_page_view (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL COMMENT '设备ID',
    slide_id BIGINT UNSIGNED COMMENT '页面ID',
    view_start_at DATETIME NOT NULL COMMENT '开始时间',
    view_end_at DATETIME COMMENT '结束时间',
    duration_sec INT COMMENT '停留时长(秒)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device (device_id),
    INDEX idx_slide (slide_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='页面访问统计表';

-- ============================================================
-- 7. 初始化数据
-- ============================================================

-- 初始化角色
INSERT INTO sys_role (code, name, description) VALUES
('super_admin', '超级管理员', '系统最高权限'),
('content_editor', '内容编辑', '内容管理与发布'),
('operator', '操作员', '日常运营管理'),
('viewer', '只读用户', '仅查看权限');

-- 初始化权限
INSERT INTO sys_permission (code, name, type, parent_id, path, sort_order) VALUES
('dashboard', '数据看板', 'menu', NULL, '/dashboard', 1),
('content', '内容管理', 'menu', NULL, '/content', 2),
('content_brand', '品牌管理', 'button', 2, '/content/brands', 1),
('content_product', '产品管理', 'button', 2, '/content/products', 2),
('content_qa', '问答管理', 'button', 2, '/content/qa', 3),
('device', '设备管理', 'menu', NULL, '/device', 3),
('device_list', '设备列表', 'button', 4, '/device/list', 1),
('device_update', '设备更新', 'button', 4, '/device/update', 2),
('user', '用户管理', 'menu', NULL, '/user', 4),
('setting', '系统设置', 'menu', NULL, '/setting', 5);

-- 超级管理员分配所有权限
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT 1, id FROM sys_permission;

-- 内容编辑权限
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(2, 1), (2, 2), (2, 3), (2, 4), (2, 5);

-- 操作员权限
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(3, 1), (3, 4), (3, 6), (3, 7);

-- 只读用户
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(4, 1);

-- 初始化默认用户 (密码: admin123, 已bcrypt加密)
INSERT INTO sys_user (username, password_hash, real_name, role_id) VALUES
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', '系统管理员', 1);

-- 初始化问答库示例
INSERT INTO biz_qa (category, question, answer, keywords, status) VALUES
('fee', '加盟费多少钱？', '加盟费根据城市等级不同：一线城市5万元，二线城市3万元，三线及以下城市2万元。具体费用根据合作模式有所差异。', '["加盟费", "多少钱", "费用", "价格"]', 1),
('fee', '保证金多少？', '保证金1万元，合作期满且无违约情况可全额退还。保证金在合同签订后7日内支付。', '["保证金", "押金", "退还"]', 1),
('roi', '多久可以回本？', '根据历史数据统计，平均回本周期为8-14个月。一线城市门店平均10个月回本，二线城市平均12个月，三线城市平均14个月。', '["回本", "周期", "多久", "回报"]', 1),
('policy', '有区域保护吗？', '有区域保护政策。根据合作级别不同，保护半径为1-3公里。区域内不再开设第二家同类门店，保障加盟商利益。', '["区域", "保护", "独家", "范围"]', 1),
('support', '总部提供什么扶持？', '总部提供全方位扶持：选址支持、装修指导、系统培训、营销方案、运营指导、供应链保障。提供开业前3天的驻店指导服务。', '["扶持", "支持", "培训", "帮助"]', 1);

-- 初始化示例品牌
INSERT INTO biz_brand (name, slogan, intro, honor_list, sort_order) VALUES
('尚航科技', '智能引领未来', '尚航科技成立于2020年，致力于用AI技术赋能传统招商行业...', '["高新技术企业","专利15项","行业创新奖"]', 1);

