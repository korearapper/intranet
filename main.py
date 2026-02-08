"""
광고를 잘 아는 사람들 — 백엔드 API v3
FastAPI + Supabase REST (no SDK) + Decodo Proxy
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, httpx, random, json, re, hashlib
from datetime import datetime, timedelta

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
PROXY_HOST = os.getenv("PROXY_HOST", "kr.decodo.com")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")
PROXY_PORT_START = int(os.getenv("PROXY_PORT_START", "10001"))
PROXY_PORT_END = int(os.getenv("PROXY_PORT_END", "19999"))
JWT_SECRET = os.getenv("JWT_SECRET", "adpeople-secret-2026")

app = FastAPI(title="AdPeople API", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SB_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}

async def sb_get(table, params=""):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=SB_HEADERS)
        return r.json() if r.status_code == 200 else []

async def sb_post(table, data):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB_HEADERS, json=data)
        return r.json() if r.status_code in (200,201) else None

async def sb_patch(table, match, data):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{SUPABASE_URL}/rest/v1/{table}?{match}", headers=SB_HEADERS, json=data)
        return r.json() if r.status_code == 200 else None

async def sb_delete(table, match):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{SUPABASE_URL}/rest/v1/{table}?{match}", headers=SB_HEADERS)
        return r.status_code in (200, 204)

def get_proxy():
    port = random.randint(PROXY_PORT_START, PROXY_PORT_END)
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{port}"

def hash_pw(pw):
    return hashlib.sha256((pw + JWT_SECRET).encode()).hexdigest()

# Models
class LoginReq(BaseModel):
    user_id: str
    password: str

class CampaignReq(BaseModel):
    client_name: str
    product_type: str = ""
    sales_type: str = "월정액"
    manager: str = ""
    monthly_price: float = 0
    status: str = "active"
    start_date: str = ""
    end_date: str = ""
    note: str = ""

class SalesReq(BaseModel):
    manager: str = ""
    product_type: str = ""
    sales_type: str = "월정액"
    company: str = ""
    payer: str = ""
    name: str = ""
    unit_price: float = 0
    sale_price: float = 0
    quantity: int = 1
    cost: float = 0
    contract_date: str = ""
    biz_number: str = ""
    tax_invoice: str = "N"
    payment_confirmed: str = "N"
    refund: str = "N"
    note: str = ""

class NoticeReq(BaseModel):
    title: str
    badge: str = "일반"
    author: str = ""

class TeamReq(BaseModel):
    name: str
    position: str = ""
    role: str = "STAFF"
    level: int = 1

class RankReq(BaseModel):
    keyword: str
    place_name: Optional[str] = None
    phone: Optional[str] = None
    rank_range: int = 300

class KHReq(BaseModel):
    place_url: str
    keyword_count: int = 30
    rank_limit: int = 5

# ====== HEALTH ======
@app.get("/")
def root():
    return {"service": "AdPeople API", "version": "3.0"}

@app.get("/health")
def health():
    return {"status": "ok", "supabase": "configured" if SUPABASE_URL else "no", "proxy": f"{PROXY_HOST}"}

# ====== AUTH ======
@app.post("/api/auth/login")
async def login(req: LoginReq):
    pw_hash = hash_pw(req.password)
    rows = await sb_get("users", f"user_id=eq.{req.user_id}&password_hash=eq.{pw_hash}")
    if not rows:
        raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다")
    user = rows[0]
    token = hashlib.sha256(f"{req.user_id}{datetime.now().isoformat()}{JWT_SECRET}".encode()).hexdigest()
    await sb_patch("users", f"id=eq.{user['id']}", {"token": token, "last_login": datetime.now().isoformat()})
    return {"success": True, "token": token, "user": {"id": user["id"], "user_id": user["user_id"], "name": user["name"], "position": user.get("position",""), "role": user.get("role","STAFF"), "level": user.get("level",1)}}

# ====== CAMPAIGNS CRUD ======
@app.get("/api/campaigns")
async def get_campaigns():
    return {"campaigns": await sb_get("campaigns", "order=created_at.desc")}

@app.post("/api/campaigns")
async def create_campaign(d: CampaignReq):
    data = d.dict()
    data["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": await sb_post("campaigns", data)}

@app.delete("/api/campaigns/{cid}")
async def del_campaign(cid: int):
    await sb_delete("campaigns", f"id=eq.{cid}")
    return {"success": True}

# ====== SALES CRUD ======
@app.get("/api/sales")
async def get_sales():
    return {"records": await sb_get("sales", "order=created_at.desc")}

@app.post("/api/sales")
async def create_sale(d: SalesReq):
    data = d.dict()
    data["billing"] = d.sale_price * d.quantity
    data["billing_vat"] = data["billing"] * 1.1
    data["cost_vat"] = d.cost * 1.1
    data["margin"] = data["billing_vat"] - data["cost_vat"]
    data["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": await sb_post("sales", data)}

@app.delete("/api/sales/{sid}")
async def del_sale(sid: int):
    await sb_delete("sales", f"id=eq.{sid}")
    return {"success": True}

# ====== NOTICES CRUD ======
@app.get("/api/notices")
async def get_notices():
    return {"notices": await sb_get("notices", "order=created_at.desc&limit=20")}

@app.post("/api/notices")
async def create_notice(d: NoticeReq):
    data = d.dict()
    data["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": await sb_post("notices", data)}

@app.delete("/api/notices/{nid}")
async def del_notice(nid: int):
    await sb_delete("notices", f"id=eq.{nid}")
    return {"success": True}

# ====== TEAM CRUD ======
@app.get("/api/team")
async def get_team():
    return {"members": await sb_get("team_members", "order=level.desc")}

@app.post("/api/team")
async def add_member(d: TeamReq):
    data = d.dict()
    data["status"] = "active"
    data["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": await sb_post("team_members", data)}

@app.delete("/api/team/{tid}")
async def del_member(tid: int):
    await sb_delete("team_members", f"id=eq.{tid}")
    return {"success": True}

# ====== PROXY ======
@app.get("/api/proxy/status")
async def proxy_status():
    p = get_proxy()
    total = PROXY_PORT_END - PROXY_PORT_START + 1
    try:
        async with httpx.AsyncClient(proxy=p, timeout=10) as c:
            r = await c.get("https://httpbin.org/ip")
            return {"status": "active", "total": total, "ip": r.json().get("origin")}
    except Exception as e:
        return {"status": "error", "total": total, "error": str(e)}

# ====== SELLER DB ======
@app.get("/api/sellerdb/search")
async def search_sellers(keyword: str, limit: int = 50):
    p = get_proxy()
    try:
        async with httpx.AsyncClient(proxy=p, timeout=20) as c:
            r = await c.get(f"https://map.naver.com/p/api/search/allSearch?query={keyword}&type=place", headers={"User-Agent": "Mozilla/5.0"})
            places = r.json().get("result", {}).get("place", {}).get("list", [])
            sellers = [{"rank": i+1, "name": p.get("name",""), "tel": p.get("tel",""), "address": p.get("address",""), "category": p.get("category",[]), "review_count": p.get("reviewCount",0), "blog_review_count": p.get("blogReviewCount",0), "rating": p.get("rating",0)} for i, p in enumerate(places[:limit])]
            return {"keyword": keyword, "count": len(sellers), "sellers": sellers}
    except Exception as e:
        raise HTTPException(500, str(e))

# ====== RANK ======
@app.post("/api/rank/check")
async def rank_check(req: RankReq):
    p = get_proxy()
    try:
        async with httpx.AsyncClient(proxy=p, timeout=20) as c:
            r = await c.get(f"https://map.naver.com/p/api/search/allSearch?query={req.keyword}&type=place", headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            plist = data.get("result",{}).get("place",{}).get("list",[])
            total = data.get("result",{}).get("place",{}).get("totalCount",0)
            for idx, pl in enumerate(plist[:req.rank_range]):
                if (req.place_name and req.place_name in pl.get("name","")) or (req.phone and req.phone in pl.get("tel","")):
                    rev = pl.get("reviewCount",0)
                    blog = pl.get("blogReviewCount",0)
                    rank = idx + 1
                    n1 = round(min(0.2 + sum(0.08 for pt in req.keyword.split() if pt in pl.get("name","")) + min(rev/10000,0.1), 0.5), 6)
                    n2 = round(min(0.2 + min(rev/5000,0.12) + min(blog/3000,0.1), 0.5), 6)
                    n3 = round(max(0, 1-(rank/max(total,1)))*0.5, 3) if total else 0
                    result = {"found": True, "keyword": req.keyword, "place_name": pl.get("name",""), "rank": rank, "n1": n1, "n2": n2, "n3": n3, "visitor_reviews": rev, "blog_reviews": blog, "total_biz": total}
                    await sb_post("rank_history", {"keyword": req.keyword, "place_name": pl.get("name",""), "rank": rank, "n1": n1, "n2": n2, "n3": n3, "visitor_reviews": rev, "blog_reviews": blog, "total_biz": total, "checked_at": datetime.now().isoformat()})
                    return result
            return {"found": False, "keyword": req.keyword, "total_biz": total}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/rank/history")
async def rank_history(keyword: str, days: int = 14):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    return {"keyword": keyword, "history": await sb_get("rank_history", f"keyword=eq.{keyword}&checked_at=gte.{since}&order=checked_at.desc")}

# ====== KEYHUNTER ======
@app.post("/api/keyhunter/analyze")
async def keyhunter(req: KHReq):
    p = get_proxy()
    try:
        place_id = None
        async with httpx.AsyncClient(proxy=p, timeout=15, follow_redirects=True) as c:
            if "naver.me" in req.place_url:
                r = await c.get(req.place_url, headers={"User-Agent": "Mozilla/5.0"})
                url = str(r.url)
            else:
                url = req.place_url
            for pat in [r'/place/(\d+)', r'placeid=(\d+)']:
                m = re.search(pat, url)
                if m: place_id = m.group(1); break
        if not place_id:
            raise HTTPException(400, "플레이스 ID를 찾을 수 없습니다")
        keywords = [f"키워드{i+1}" for i in range(req.keyword_count)]
        return {"place": {"id": place_id, "url": url}, "stats": {"generated": req.keyword_count, "qualified": 0}, "keywords": []}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
