"""
광고를 잘 아는 사람들 — 백엔드 API v2
FastAPI + Supabase + Decodo Proxy + Auth + CRUD
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os, httpx, random, json, re, hashlib
from datetime import datetime, timedelta
from supabase import create_client, Client

# ===== ENV =====
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
PROXY_HOST = os.getenv("PROXY_HOST", "kr.decodo.com")
PROXY_USER = os.getenv("PROXY_USER", "spuqtp2czv")
PROXY_PASS = os.getenv("PROXY_PASS", "1voaShrNj_2f4V3hgB")
PROXY_PORT_START = int(os.getenv("PROXY_PORT_START", "10001"))
PROXY_PORT_END = int(os.getenv("PROXY_PORT_END", "19999"))
JWT_SECRET = os.getenv("JWT_SECRET", "adpeople-secret-2026")

# ===== APP =====
app = FastAPI(title="광고를 잘 아는 사람들 API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== SUPABASE =====
def get_sb() -> Optional[Client]:
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

# ===== PROXY =====
def get_proxy() -> str:
    port = random.randint(PROXY_PORT_START, PROXY_PORT_END)
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{port}"

def get_proxy_pool(count=10):
    return [get_proxy() for _ in range(count)]

# ===== AUTH MODELS =====
class LoginReq(BaseModel):
    user_id: str
    password: str

class RegisterReq(BaseModel):
    user_id: str
    password: str
    name: str
    position: str = ""
    role: str = "STAFF"
    level: int = 1

# ===== CRUD MODELS =====
class SalesRecord(BaseModel):
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

class CampaignRecord(BaseModel):
    client_name: str
    product_type: str
    sales_type: str = "월정액"
    manager: str = ""
    monthly_price: float = 0
    status: str = "active"
    start_date: str = ""
    end_date: str = ""
    note: str = ""

class NoticeRecord(BaseModel):
    title: str
    content: str = ""
    badge: str = "일반"
    author: str = ""

class TeamRecord(BaseModel):
    name: str
    position: str = ""
    role: str = "STAFF"
    level: int = 1

class KeyHunterReq(BaseModel):
    place_url: str
    keyword_count: int = 30
    rank_limit: int = 5

class RankCheckReq(BaseModel):
    keyword: str
    place_name: Optional[str] = None
    phone: Optional[str] = None
    rank_range: int = 300

# ===== AUTH =====
def hash_pw(pw: str) -> str:
    return hashlib.sha256((pw + JWT_SECRET).encode()).hexdigest()

async def verify_token(authorization: Optional[str] = Header(None)):
    """간단 토큰 검증 — 헤더에 user_id 기반 토큰"""
    if not authorization:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    token = authorization.replace("Bearer ", "")
    sb = get_sb()
    if not sb:
        raise HTTPException(status_code=500, detail="DB not configured")
    result = sb.table("users").select("*").eq("token", token).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    return result.data[0]

# ================================================================
# HEALTH & ROOT
# ================================================================
@app.get("/")
def root():
    return {"service": "광고를 잘 아는 사람들 API", "version": "2.0.0", "status": "running"}

@app.get("/health")
def health():
    sb = get_sb()
    return {"status": "ok", "supabase": "connected" if sb else "not configured", "proxy": f"{PROXY_HOST} ({PROXY_PORT_END-PROXY_PORT_START+1} ports)"}

# ================================================================
# AUTH — 로그인 / 회원가입
# ================================================================
@app.post("/api/auth/login")
async def login(req: LoginReq):
    sb = get_sb()
    if not sb:
        raise HTTPException(status_code=500, detail="DB not configured")
    
    pw_hash = hash_pw(req.password)
    result = sb.table("users").select("*").eq("user_id", req.user_id).eq("password_hash", pw_hash).execute()
    
    if not result.data:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")
    
    user = result.data[0]
    # 토큰 갱신
    token = hashlib.sha256(f"{req.user_id}{datetime.now().isoformat()}{JWT_SECRET}".encode()).hexdigest()
    sb.table("users").update({"token": token, "last_login": datetime.now().isoformat()}).eq("id", user["id"]).execute()
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "user_id": user["user_id"],
            "name": user["name"],
            "position": user.get("position", ""),
            "role": user.get("role", "STAFF"),
            "level": user.get("level", 1)
        }
    }

@app.post("/api/auth/register")
async def register(req: RegisterReq):
    sb = get_sb()
    if not sb:
        raise HTTPException(status_code=500, detail="DB not configured")
    
    # 중복 체크
    existing = sb.table("users").select("id").eq("user_id", req.user_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다")
    
    pw_hash = hash_pw(req.password)
    token = hashlib.sha256(f"{req.user_id}{datetime.now().isoformat()}{JWT_SECRET}".encode()).hexdigest()
    
    result = sb.table("users").insert({
        "user_id": req.user_id,
        "password_hash": pw_hash,
        "name": req.name,
        "position": req.position,
        "role": req.role,
        "level": req.level,
        "token": token,
        "created_at": datetime.now().isoformat()
    }).execute()
    
    return {"success": True, "token": token}

@app.get("/api/auth/me")
async def get_me(user=Depends(verify_token)):
    return {"user": {k: v for k, v in user.items() if k != "password_hash"}}

# ================================================================
# PROXY STATUS
# ================================================================
@app.get("/api/proxy/status")
async def proxy_status():
    test_proxy = get_proxy()
    total = PROXY_PORT_END - PROXY_PORT_START + 1
    try:
        async with httpx.AsyncClient(proxy=test_proxy, timeout=10) as client:
            r = await client.get("https://httpbin.org/ip")
            return {"status": "active", "host": PROXY_HOST, "total_ports": total, "test_ip": r.json().get("origin"), "response_ms": int(r.elapsed.total_seconds()*1000)}
    except Exception as e:
        return {"status": "error", "host": PROXY_HOST, "total_ports": total, "error": str(e)}

# ================================================================
# CAMPAIGNS — CRUD
# ================================================================
@app.get("/api/campaigns")
async def get_campaigns(status: Optional[str] = None):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    q = sb.table("campaigns").select("*").order("created_at", desc=True)
    if status: q = q.eq("status", status)
    return {"campaigns": q.execute().data}

@app.post("/api/campaigns")
async def create_campaign(data: CampaignRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    d = data.dict()
    d["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": sb.table("campaigns").insert(d).execute().data}

@app.put("/api/campaigns/{cid}")
async def update_campaign(cid: int, data: CampaignRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    return {"success": True, "data": sb.table("campaigns").update(data.dict()).eq("id", cid).execute().data}

@app.delete("/api/campaigns/{cid}")
async def delete_campaign(cid: int):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    sb.table("campaigns").delete().eq("id", cid).execute()
    return {"success": True}

# ================================================================
# SALES — CRUD
# ================================================================
@app.get("/api/sales")
async def get_sales(month: Optional[str] = None):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    q = sb.table("sales").select("*").order("contract_date", desc=True)
    if month: q = q.like("contract_date", f"{month}%")
    return {"records": q.execute().data}

@app.post("/api/sales")
async def create_sale(rec: SalesRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    d = rec.dict()
    d["billing"] = rec.sale_price * rec.quantity
    d["billing_vat"] = d["billing"] * 1.1
    d["cost_vat"] = rec.cost * 1.1
    d["margin"] = d["billing_vat"] - d["cost_vat"]
    d["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": sb.table("sales").insert(d).execute().data}

@app.put("/api/sales/{sid}")
async def update_sale(sid: int, rec: SalesRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    d = rec.dict()
    d["billing"] = rec.sale_price * rec.quantity
    d["billing_vat"] = d["billing"] * 1.1
    d["cost_vat"] = rec.cost * 1.1
    d["margin"] = d["billing_vat"] - d["cost_vat"]
    return {"success": True, "data": sb.table("sales").update(d).eq("id", sid).execute().data}

@app.delete("/api/sales/{sid}")
async def delete_sale(sid: int):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    sb.table("sales").delete().eq("id", sid).execute()
    return {"success": True}

# ================================================================
# NOTICES — CRUD
# ================================================================
@app.get("/api/notices")
async def get_notices():
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    return {"notices": sb.table("notices").select("*").order("created_at", desc=True).limit(20).execute().data}

@app.post("/api/notices")
async def create_notice(data: NoticeRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    d = data.dict()
    d["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": sb.table("notices").insert(d).execute().data}

@app.put("/api/notices/{nid}")
async def update_notice(nid: int, data: NoticeRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    return {"success": True, "data": sb.table("notices").update(data.dict()).eq("id", nid).execute().data}

@app.delete("/api/notices/{nid}")
async def delete_notice(nid: int):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    sb.table("notices").delete().eq("id", nid).execute()
    return {"success": True}

# ================================================================
# TEAM — CRUD
# ================================================================
@app.get("/api/team")
async def get_team():
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    return {"members": sb.table("team_members").select("*").order("level", desc=True).execute().data}

@app.post("/api/team")
async def add_member(data: TeamRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    d = data.dict()
    d["status"] = "active"
    d["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": sb.table("team_members").insert(d).execute().data}

@app.put("/api/team/{tid}")
async def update_member(tid: int, data: TeamRecord):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    return {"success": True, "data": sb.table("team_members").update(data.dict()).eq("id", tid).execute().data}

@app.delete("/api/team/{tid}")
async def delete_member(tid: int):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    sb.table("team_members").delete().eq("id", tid).execute()
    return {"success": True}

# ================================================================
# KEYHUNTER
# ================================================================
@app.post("/api/keyhunter/analyze")
async def keyhunter_analyze(req: KeyHunterReq):
    place_info = await fetch_place_info(req.place_url)
    if not place_info:
        raise HTTPException(400, "플레이스 URL을 확인해주세요")
    keywords = generate_keywords(place_info, req.keyword_count)
    ranked = await check_ranks(keywords, place_info, req.rank_limit)
    organic = [kw for kw in ranked if kw["type"] == "organic"]
    sb = get_sb()
    if sb:
        sb.table("keyhunter_results").insert({"place_url": req.place_url, "place_name": place_info.get("name",""), "total_generated": len(keywords), "total_organic": len(organic), "results": json.dumps(organic, ensure_ascii=False), "created_at": datetime.now().isoformat()}).execute()
    return {"place": place_info, "stats": {"generated": len(keywords), "qualified": len(organic), "cpc_excluded": len(ranked)-len(organic), "out_of_rank": len(keywords)-len(ranked)}, "keywords": organic}

async def fetch_place_info(url):
    proxy = get_proxy()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://map.naver.com/"}
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=15, follow_redirects=True) as client:
            if "naver.me" in url:
                r = await client.get(url, headers=headers)
                url = str(r.url)
            place_id = None
            for p in [r'/place/(\d+)', r'placeid=(\d+)', r'/restaurant/(\d+)']:
                m = re.search(p, url)
                if m: place_id = m.group(1); break
            if not place_id: return None
            return {"id": place_id, "name": "업체명", "category": "카테고리", "address": "주소", "phone": "", "tags": [], "menus": [], "url": url}
    except Exception as e:
        print(f"Place fetch error: {e}")
        return None

def generate_keywords(place_info, count):
    keywords = []
    cat = place_info.get("category","")
    addr = place_info.get("address","")
    regions = addr.split()[:3] if addr else []
    for r in regions:
        keywords += [f"{r} {cat}", f"{r} {cat} 맛집", f"{r} {cat} 추천"]
    for r in regions[:2]:
        for s in ["회식","데이트","가족식사","모임","점심","저녁"]:
            keywords.append(f"{r} {s}")
    return list(dict.fromkeys(keywords))[:count]

async def check_ranks(keywords, place_info, rank_limit):
    results = []
    proxies = get_proxy_pool(20)
    for i, kw in enumerate(keywords):
        try:
            rd = await search_naver_place(kw, place_info, proxies[i%len(proxies)], rank_limit)
            if rd: results.append(rd)
        except: pass
    return results

async def search_naver_place(keyword, place_info, proxy, rank_limit):
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=15) as client:
            r = await client.get(f"https://map.naver.com/p/api/search/allSearch?query={keyword}&type=place", headers={"User-Agent":"Mozilla/5.0","Referer":"https://map.naver.com/"})
            data = r.json()
            for idx, p in enumerate(data.get("result",{}).get("place",{}).get("list",[])):
                if str(p.get("id")) == place_info.get("id") or p.get("name") == place_info.get("name"):
                    rank = idx+1
                    if rank <= rank_limit:
                        is_ad = p.get("isAdPlace",False) or p.get("adId")
                        return {"keyword":keyword,"rank":rank,"type":"cpc" if is_ad else "organic","monthly_search":0,"competition":"medium"}
    except: pass
    return None

# ================================================================
# RANK MONITOR
# ================================================================
@app.post("/api/rank/check")
async def rank_check(req: RankCheckReq):
    proxy = get_proxy()
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=20) as client:
            r = await client.get(f"https://map.naver.com/p/api/search/allSearch?query={req.keyword}&type=place", headers={"User-Agent":"Mozilla/5.0","Referer":"https://map.naver.com/"})
            data = r.json()
            place_list = data.get("result",{}).get("place",{}).get("list",[])
            total_biz = data.get("result",{}).get("place",{}).get("totalCount",0)
            target = None; target_rank = 0
            for idx, p in enumerate(place_list[:req.rank_range]):
                if (req.place_name and req.place_name in p.get("name","")) or (req.phone and req.phone in p.get("tel","")):
                    target = p; target_rank = idx+1; break
            if not target:
                return {"found":False,"keyword":req.keyword,"total_biz":total_biz}
            reviews = target.get("reviewCount",0)
            blog = target.get("blogReviewCount",0)
            n1 = min(0.2 + sum(0.08 for pt in req.keyword.split() if pt in target.get("name","")) + min(reviews/10000,0.1), 0.5)
            n2 = min(0.2 + min(reviews/5000,0.12) + min(blog/3000,0.1), 0.5)
            n3 = round(max(0,1-(target_rank/max(total_biz,1)))*0.5, 3) if total_biz else 0
            result = {"found":True,"keyword":req.keyword,"place_name":target.get("name",""),"rank":target_rank,"n1":round(n1,6),"n2":round(n2,6),"n3":n3,"visitor_reviews":reviews,"blog_reviews":blog,"total_biz":total_biz,"checked_at":datetime.now().isoformat()}
            sb = get_sb()
            if sb:
                sb.table("rank_history").insert({"keyword":req.keyword,"place_name":target.get("name",""),"rank":target_rank,"n1":result["n1"],"n2":result["n2"],"n3":result["n3"],"visitor_reviews":reviews,"blog_reviews":blog,"total_biz":total_biz,"checked_at":datetime.now().isoformat()}).execute()
            return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/rank/history")
async def rank_history(keyword: str, days: int = 14):
    sb = get_sb()
    if not sb: raise HTTPException(500, "DB error")
    since = (datetime.now()-timedelta(days=days)).isoformat()
    return {"keyword":keyword,"history":sb.table("rank_history").select("*").eq("keyword",keyword).gte("checked_at",since).order("checked_at",desc=True).execute().data}

# ================================================================
# SELLER DB
# ================================================================
@app.get("/api/sellerdb/search")
async def search_sellers(keyword: str, platform: str = "naver_place", limit: int = 50):
    proxy = get_proxy()
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=20) as client:
            r = await client.get(f"https://map.naver.com/p/api/search/allSearch?query={keyword}&type=place", headers={"User-Agent":"Mozilla/5.0"})
            places = r.json().get("result",{}).get("place",{}).get("list",[])
            sellers = [{"rank":i+1,"name":p.get("name",""),"tel":p.get("tel",""),"address":p.get("address",""),"category":p.get("category",[]),"review_count":p.get("reviewCount",0),"blog_review_count":p.get("blogReviewCount",0),"rating":p.get("rating",0)} for i,p in enumerate(places[:limit])]
            sb = get_sb()
            if sb:
                sb.table("seller_db").insert({"keyword":keyword,"platform":platform,"count":len(sellers),"results":json.dumps(sellers,ensure_ascii=False),"created_at":datetime.now().isoformat()}).execute()
            return {"keyword":keyword,"count":len(sellers),"sellers":sellers}
    except Exception as e:
        raise HTTPException(500, str(e))
