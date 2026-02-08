-- =============================================
-- 광고를 잘 아는 사람들 — Supabase 스키마
-- 새 프로젝트 생성 후 SQL Editor에서 실행
-- =============================================

-- 1. 매출 관리
CREATE TABLE sales (
    id BIGSERIAL PRIMARY KEY,
    manager TEXT NOT NULL,
    product_type TEXT NOT NULL,
    sales_type TEXT NOT NULL DEFAULT '월정액',
    company TEXT NOT NULL,
    payer TEXT,
    name TEXT,
    unit_price NUMERIC DEFAULT 0,
    sale_price NUMERIC DEFAULT 0,
    quantity INTEGER DEFAULT 1,
    billing NUMERIC DEFAULT 0,
    billing_vat NUMERIC DEFAULT 0,
    cost NUMERIC DEFAULT 0,
    cost_vat NUMERIC DEFAULT 0,
    margin NUMERIC DEFAULT 0,
    contract_date DATE,
    biz_number TEXT,
    tax_invoice TEXT DEFAULT 'N',
    payment_confirmed TEXT DEFAULT 'N',
    refund TEXT DEFAULT 'N',
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 캠페인 관리
CREATE TABLE campaigns (
    id BIGSERIAL PRIMARY KEY,
    client_name TEXT NOT NULL,
    product_type TEXT NOT NULL,
    sales_type TEXT DEFAULT '월정액',
    manager TEXT,
    monthly_price NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 순위 이력
CREATE TABLE rank_history (
    id BIGSERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    place_name TEXT,
    rank INTEGER,
    n1 NUMERIC(10,6),
    n2 NUMERIC(10,6),
    n3 NUMERIC(10,3),
    visitor_reviews INTEGER DEFAULT 0,
    blog_reviews INTEGER DEFAULT 0,
    total_biz INTEGER DEFAULT 0,
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. KeyHunter 분석 결과
CREATE TABLE keyhunter_results (
    id BIGSERIAL PRIMARY KEY,
    place_url TEXT,
    place_name TEXT,
    total_generated INTEGER DEFAULT 0,
    total_organic INTEGER DEFAULT 0,
    results JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 영업DB
CREATE TABLE seller_db (
    id BIGSERIAL PRIMARY KEY,
    keyword TEXT,
    platform TEXT DEFAULT 'naver_place',
    count INTEGER DEFAULT 0,
    results JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 팀원 관리
CREATE TABLE team_members (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT,
    role TEXT DEFAULT 'STAFF',
    level INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. 공지사항
CREATE TABLE notices (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    badge TEXT DEFAULT '일반',
    author TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===== 인덱스 =====
CREATE INDEX idx_sales_contract_date ON sales(contract_date);
CREATE INDEX idx_sales_company ON sales(company);
CREATE INDEX idx_rank_keyword ON rank_history(keyword);
CREATE INDEX idx_rank_checked ON rank_history(checked_at);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- ===== 초기 데이터 =====
INSERT INTO team_members (name, position, role, level) VALUES
('대표', '대표이사', 'ADMIN', 5),
('김민수', '팀장', 'MANAGER', 4),
('박지영', '대리', 'STAFF', 3),
('이서연', '사원', 'STAFF', 3);

INSERT INTO notices (title, badge, author) VALUES
('키워드 도구 등급 변경 — Lv.3 이상 KeyHunter 이용', '중요', '대표'),
('프록시 풀 교체 완료 — kr.decodo.com 10,000포트', '안내', '대표'),
('순위 모니터링 300위 확대 + N1/N2/N3 추가', '업데이트', '대표'),
('2월 정산 마감 — 2/25(화) 세금계산서 발행', '안내', '대표'),
('인트라넷 v2.0 오픈 — 스프레드시트 기능 추가', '일반', '대표');
