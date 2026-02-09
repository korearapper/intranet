"""AdPeople API v3 — No Supabase SDK, REST only"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, httpx, random, json, re, hashlib, uvicorn
from datetime import datetime, timedelta

SB_URL = os.getenv("SUPABASE_URL", "")
SB_KEY = os.getenv("SUPABASE_KEY", "")
PX_HOST = os.getenv("PROXY_HOST", "kr.decodo.com")
PX_USER = os.getenv("PROXY_USER", "")
PX_PASS = os.getenv("PROXY_PASS", "")
PX_START = int(os.getenv("PROXY_PORT_START", "10001"))
PX_END = int(os.getenv("PROXY_PORT_END", "19999"))
SECRET = os.getenv("JWT_SECRET", "adpeople-secret-2026")

app = FastAPI(title="AdPeople API", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}

async def sg(t, q=""):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{SB_URL}/rest/v1/{t}?{q}", headers=H)
        return r.json() if r.status_code == 200 else []

async def sp(t, d):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{SB_URL}/rest/v1/{t}", headers=H, json=d)
        return r.json() if r.status_code in (200,201) else None

async def su(t, m, d):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.patch(f"{SB_URL}/rest/v1/{t}?{m}", headers=H, json=d)
        return r.json() if r.status_code == 200 else None

async def sd(t, m):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.delete(f"{SB_URL}/rest/v1/{t}?{m}", headers=H)
        return r.status_code in (200,204)

def px():
    return f"http://{PX_USER}:{PX_PASS}@{PX_HOST}:{random.randint(PX_START, PX_END)}"

def hpw(pw):
    return hashlib.sha256((pw + SECRET).encode()).hexdigest()

class LoginReq(BaseModel):
    user_id: str
    password: str
class CampReq(BaseModel):
    client_name: str; product_type: str = ""; sales_type: str = "월정액"; manager: str = ""; monthly_price: float = 0; status: str = "active"; start_date: str = ""; note: str = ""
class SaleReq(BaseModel):
    manager: str = ""; product_type: str = ""; sales_type: str = "월정액"; company: str = ""; payer: str = ""; name: str = ""; unit_price: float = 0; sale_price: float = 0; quantity: int = 1; cost: float = 0; contract_date: str = ""; biz_number: str = ""; tax_invoice: str = "N"; payment_confirmed: str = "N"; refund: str = "N"; note: str = ""
class NoticeReq(BaseModel):
    title: str; badge: str = "일반"; author: str = ""
class TeamReq(BaseModel):
    name: str; position: str = ""; role: str = "STAFF"; level: int = 1
class RankReq(BaseModel):
    keyword: str; place_name: Optional[str] = None; phone: Optional[str] = None; rank_range: int = 300

@app.get("/")
def root():
    return {"service": "AdPeople API", "v": "3.0"}

@app.get("/health")
def health():
    return {"status": "ok", "sb": bool(SB_URL), "px": PX_HOST}

@app.post("/api/auth/login")
async def login(r: LoginReq):
    h = hpw(r.password)
    rows = await sg("users", f"user_id=eq.{r.user_id}&password_hash=eq.{h}")
    if not rows:
        raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다")
    u = rows[0]
    tk = hashlib.sha256(f"{r.user_id}{datetime.now().isoformat()}{SECRET}".encode()).hexdigest()
    await su("users", f"id=eq.{u['id']}", {"token": tk, "last_login": datetime.now().isoformat()})
    return {"success": True, "token": tk, "user": {"id": u["id"], "user_id": u["user_id"], "name": u["name"], "position": u.get("position",""), "role": u.get("role","STAFF"), "level": u.get("level",1)}}

@app.get("/api/campaigns")
async def get_camp():
    return {"campaigns": await sg("campaigns", "order=created_at.desc")}
@app.post("/api/campaigns")
async def add_camp(d: CampReq):
    return {"success": True, "data": await sp("campaigns", {**d.dict(), "created_at": datetime.now().isoformat()})}
@app.delete("/api/campaigns/{i}")
async def del_camp(i: int):
    await sd("campaigns", f"id=eq.{i}"); return {"success": True}

@app.get("/api/sales")
async def get_sales():
    return {"records": await sg("sales", "order=created_at.desc")}
@app.post("/api/sales")
async def add_sale(d: SaleReq):
    x = d.dict(); x["billing"] = d.sale_price*d.quantity; x["billing_vat"] = x["billing"]*1.1; x["cost_vat"] = d.cost*1.1; x["margin"] = x["billing_vat"]-x["cost_vat"]; x["created_at"] = datetime.now().isoformat()
    return {"success": True, "data": await sp("sales", x)}
@app.delete("/api/sales/{i}")
async def del_sale(i: int):
    await sd("sales", f"id=eq.{i}"); return {"success": True}

@app.get("/api/notices")
async def get_notices():
    return {"notices": await sg("notices", "order=created_at.desc&limit=20")}
@app.post("/api/notices")
async def add_notice(d: NoticeReq):
    return {"success": True, "data": await sp("notices", {**d.dict(), "created_at": datetime.now().isoformat()})}
@app.delete("/api/notices/{i}")
async def del_notice(i: int):
    await sd("notices", f"id=eq.{i}"); return {"success": True}

@app.get("/api/team")
async def get_team():
    return {"members": await sg("team_members", "order=level.desc")}
@app.post("/api/team")
async def add_team(d: TeamReq):
    return {"success": True, "data": await sp("team_members", {**d.dict(), "status": "active", "created_at": datetime.now().isoformat()})}
@app.delete("/api/team/{i}")
async def del_team(i: int):
    await sd("team_members", f"id=eq.{i}"); return {"success": True}

@app.get("/api/sellerdb/search")
async def sellers(keyword: str, limit: int = 50):
    try:
        async with httpx.AsyncClient(proxy=px(), timeout=20) as c:
            r = await c.get(f"https://map.naver.com/p/api/search/allSearch?query={keyword}&type=place", headers={"User-Agent":"Mozilla/5.0"})
            pl = r.json().get("result",{}).get("place",{}).get("list",[])
            return {"keyword": keyword, "count": len(pl[:limit]), "sellers": [{"rank":i+1,"name":p.get("name",""),"tel":p.get("tel",""),"address":p.get("address",""),"category":p.get("category",[]),"review_count":p.get("reviewCount",0),"rating":p.get("rating",0)} for i,p in enumerate(pl[:limit])]}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/rank/check")
async def rank_check(req: RankReq):
    try:
        async with httpx.AsyncClient(proxy=px(), timeout=20) as c:
            r = await c.get(f"https://map.naver.com/p/api/search/allSearch?query={req.keyword}&type=place", headers={"User-Agent":"Mozilla/5.0"})
            d = r.json(); pl = d.get("result",{}).get("place",{}).get("list",[]); tot = d.get("result",{}).get("place",{}).get("totalCount",0)
            for idx,p in enumerate(pl[:req.rank_range]):
                if (req.place_name and req.place_name in p.get("name","")) or (req.phone and req.phone in p.get("tel","")):
                    rk=idx+1; rv=p.get("reviewCount",0); bl=p.get("blogReviewCount",0)
                    n1=round(min(.2+min(rv/10000,.1),.5),6); n2=round(min(.2+min(rv/5000,.12)+min(bl/3000,.1),.5),6); n3=round(max(0,1-(rk/max(tot,1)))*.5,3)
                    await sp("rank_history",{"keyword":req.keyword,"place_name":p.get("name",""),"rank":rk,"n1":n1,"n2":n2,"n3":n3,"visitor_reviews":rv,"blog_reviews":bl,"total_biz":tot,"checked_at":datetime.now().isoformat()})
                    return {"found":True,"keyword":req.keyword,"place_name":p.get("name",""),"rank":rk,"n1":n1,"n2":n2,"n3":n3,"visitor_reviews":rv,"blog_reviews":bl,"total_biz":tot}
            return {"found":False,"keyword":req.keyword,"total_biz":tot}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/rank/history")
async def rank_hist(keyword: str, days: int = 14):
    since = (datetime.now()-timedelta(days=days)).isoformat()
    return {"keyword": keyword, "history": await sg("rank_history", f"keyword=eq.{keyword}&checked_at=gte.{since}&order=checked_at.desc")}

@app.get("/api/proxy/status")
async def px_status():
    try:
        async with httpx.AsyncClient(proxy=px(), timeout=10) as c:
            r = await c.get("https://httpbin.org/ip")
            return {"status":"active","ip":r.json().get("origin")}
    except Exception as e:
        return {"status":"error","error":str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
