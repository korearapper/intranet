-- =============================================
-- v2 추가: users 테이블 (로그인용)
-- Supabase SQL Editor에서 실행
-- =============================================

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    position TEXT DEFAULT '',
    role TEXT DEFAULT 'STAFF',
    level INTEGER DEFAULT 1,
    token TEXT,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_userid ON users(user_id);
CREATE INDEX idx_users_token ON users(token);

-- 초기 관리자 계정
-- ID: admin / PW: admin1234 (SHA256 해시)
INSERT INTO users (user_id, password_hash, name, position, role, level) VALUES
('admin', 'ad66a0b77701a1d91d95ab8d9e12a3811c6028189d7523eac655533e8e1ecae1', '대표', '대표이사', 'ADMIN', 5);
