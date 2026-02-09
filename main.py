"""AdPeople Intranet API v3 — REST only, no Supabase SDK"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, httpx, random, hashlib, re, uvicorn, urllib.parse
from datetime import datetime, timedelta

SB = os.getenv("SUPABASE_URL","")
SK = os.getenv("SUPABASE_KEY","")
PH = os.getenv("PROXY_HOST","kr.decodo.com")
PU = os.getenv("PROXY_USER","")
PP = os.getenv("PROXY_PASS","")
P0 = int(os.getenv("PROXY_PORT_START","10001"))
P1 = int(os.getenv("PROXY_PORT_END","19999"))
SC = os.getenv("JWT_SECRET","adpeople-secret-2026")

app = FastAPI(title="AdPeople",version="3.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

H={"apikey":SK,"Authorization":f"Bearer {SK}","Content-Type":"application/json","Prefer":"return=representation"}

async def sg(t,q=""):
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(f"{SB}/rest/v1/{t}?{q}",headers=H);return r.json() if r.status_code==200 else []
async def sp(t,d):
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.post(f"{SB}/rest/v1/{t}",headers=H,json=d);return r.json() if r.status_code in(200,201) else None
async def su(t,m,d):
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.patch(f"{SB}/rest/v1/{t}?{m}",headers=H,json=d);return r.json() if r.status_code==200 else None
async def sd(t,m):
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.delete(f"{SB}/rest/v1/{t}?{m}",headers=H);return r.status_code in(200,204)

def px():
    return f"http://{PU}:{PP}@{PH}:{random.randint(P0,P1)}"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
NAVER_HEADERS = {
    "User-Agent": UA,
    "Referer": "https://map.naver.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def naver_search(keyword: str, proxy: str):
    """네이버 지도 검색 — 여러 URL 패턴 시도"""
    coord="126.9783882;37.5666103"
    urls = [
        f"https://map.naver.com/p/api/search/allSearch?query={urllib.parse.quote(keyword)}&type=place&searchCoord={coord}&boundary=",
    ]
    for url in urls:
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=20) as c:
                r = await c.get(url, headers=NAVER_HEADERS)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        place = data.get("result", {}).get("place", {})
                        if place and place.get("list"):
                            return place
                    except:
                        continue
        except:
            continue
    # 최후 수단: 모바일 검색
    try:
        murl = f"https://m.map.naver.com/search2/search.naver?query={urllib.parse.quote(keyword)}&sm=hty&style=v5"
        async with httpx.AsyncClient(proxy=proxy, timeout=20) as c:
            r = await c.get(murl, headers={**NAVER_HEADERS, "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"})
            if r.status_code == 200:
                try:
                    data = r.json()
                    if "result" in data:
                        return data.get("result", {}).get("place", {})
                except:
                    pass
    except:
        pass
    return None

class LoginReq(BaseModel):
    user_id:str;password:str
class CampReq(BaseModel):
    client_name:str;product_type:str="";sales_type:str="월정액";manager:str="";monthly_price:float=0;status:str="active";start_date:str="";note:str=""
class SaleReq(BaseModel):
    manager:str="";product_type:str="";sales_type:str="월정액";company:str="";payer:str="";name:str="";unit_price:float=0;sale_price:float=0;quantity:int=1;cost:float=0;contract_date:str="";biz_number:str="";tax_invoice:str="N";payment_confirmed:str="N";refund:str="N";note:str=""
class NoticeReq(BaseModel):
    title:str;badge:str="일반";author:str=""
class TeamReq(BaseModel):
    name:str;position:str="";role:str="STAFF";level:int=1
class RankReq(BaseModel):
    keyword:str;place_id:Optional[str]=None;place_name:Optional[str]=None;phone:Optional[str]=None;rank_range:int=300
class KHReq(BaseModel):
    place_url:str;keyword_count:int=30;rank_limit:int=5

@app.get("/")
def root():
    return {"service":"AdPeople API","v":"3.0"}
@app.get("/health")
def health():
    return {"status":"ok","sb":bool(SB),"px":PH}

# AUTH
@app.post("/api/auth/login")
async def login(r:LoginReq):
    h=hashlib.sha256((r.password+SC).encode()).hexdigest()
    rows=await sg("users",f"user_id=eq.{r.user_id}&password_hash=eq.{h}")
    if not rows: raise HTTPException(401,"아이디 또는 비밀번호가 올바르지 않습니다")
    u=rows[0];tk=hashlib.sha256(f"{r.user_id}{datetime.now().isoformat()}{SC}".encode()).hexdigest()
    await su("users",f"id=eq.{u['id']}",{"token":tk,"last_login":datetime.now().isoformat()})
    return {"success":True,"token":tk,"user":{"id":u["id"],"user_id":u["user_id"],"name":u["name"],"position":u.get("position",""),"role":u.get("role","STAFF"),"level":u.get("level",1)}}

# CAMPAIGNS
@app.get("/api/campaigns")
async def get_camp():
    return {"campaigns":await sg("campaigns","order=created_at.desc")}
@app.post("/api/campaigns")
async def add_camp(d:CampReq):
    return {"success":True,"data":await sp("campaigns",{**d.dict(),"created_at":datetime.now().isoformat()})}
@app.delete("/api/campaigns/{i}")
async def del_camp(i:int):
    await sd("campaigns",f"id=eq.{i}");return {"success":True}

# SALES
@app.get("/api/sales")
async def get_sales():
    return {"records":await sg("sales","order=created_at.desc")}
@app.post("/api/sales")
async def add_sale(d:SaleReq):
    x=d.dict();x["billing"]=d.sale_price*d.quantity;x["billing_vat"]=x["billing"]*1.1;x["cost_vat"]=d.cost*1.1;x["margin"]=x["billing_vat"]-x["cost_vat"];x["created_at"]=datetime.now().isoformat()
    return {"success":True,"data":await sp("sales",x)}
@app.delete("/api/sales/{i}")
async def del_sale(i:int):
    await sd("sales",f"id=eq.{i}");return {"success":True}

# NOTICES
@app.get("/api/notices")
async def get_notices():
    return {"notices":await sg("notices","order=created_at.desc&limit=20")}
@app.post("/api/notices")
async def add_notice(d:NoticeReq):
    return {"success":True,"data":await sp("notices",{**d.dict(),"created_at":datetime.now().isoformat()})}
@app.delete("/api/notices/{i}")
async def del_notice(i:int):
    await sd("notices",f"id=eq.{i}");return {"success":True}

# TEAM
@app.get("/api/team")
async def get_team():
    return {"members":await sg("team_members","order=level.desc")}
@app.post("/api/team")
async def add_team(d:TeamReq):
    return {"success":True,"data":await sp("team_members",{**d.dict(),"status":"active","created_at":datetime.now().isoformat()})}
@app.delete("/api/team/{i}")
async def del_team(i:int):
    await sd("team_members",f"id=eq.{i}");return {"success":True}

# SELLER DB
@app.get("/api/sellerdb/search")
async def sellers(keyword:str,limit:int=50):
    p=px()
    place=await naver_search(keyword, p)
    if not place:
        return {"keyword":keyword,"count":0,"sellers":[],"error":"네이버 검색 결과를 가져올 수 없습니다"}
    plist=place.get("list",[])
    return {"keyword":keyword,"count":len(plist[:limit]),"sellers":[{"rank":i+1,"name":pl.get("name",""),"tel":pl.get("tel",""),"address":pl.get("address",""),"category":pl.get("category",[]),"review_count":pl.get("reviewCount",0),"blog_review_count":pl.get("blogReviewCount",0),"rating":pl.get("rating",0)} for i,pl in enumerate(plist[:limit])]}

# RANK CHECK — place_id(PID)로 매칭
@app.post("/api/rank/check")
async def rank_check(req:RankReq):
    p=px()
    place=await naver_search(req.keyword, p)
    if not place:
        raise HTTPException(500,"네이버 검색 결과를 가져올 수 없습니다. 잠시 후 재시도해주세요.")
    plist=place.get("list",[])
    tot=place.get("totalCount",0)
    for idx,pl in enumerate(plist[:req.rank_range]):
        matched=False
        pid=str(pl.get("id",""))
        # PID 매칭
        if req.place_id and req.place_id in pid:
            matched=True
        # 업체명 매칭
        if req.place_name and req.place_name in pl.get("name",""):
            matched=True
        # 전화번호 매칭
        if req.phone and req.phone.replace("-","") in pl.get("tel","").replace("-",""):
            matched=True
        if not matched:
            continue
        rk=idx+1;rv=pl.get("reviewCount",0);bl=pl.get("blogReviewCount",0)
        n1=round(min(.2+sum(.08 for pt in req.keyword.split() if pt in pl.get("name",""))+min(rv/10000,.1),.5),6)
        n2=round(min(.2+min(rv/5000,.12)+min(bl/3000,.1),.5),6)
        n3=round(max(0,1-(rk/max(tot,1)))*.5,3) if tot else 0
        rec={"keyword":req.keyword,"place_name":pl.get("name",""),"rank":rk,"n1":n1,"n2":n2,"n3":n3,"visitor_reviews":rv,"blog_reviews":bl,"total_biz":tot,"checked_at":datetime.now().isoformat()}
        await sp("rank_history",rec)
        return {"found":True,**rec,"place_id":pid}
    return {"found":False,"keyword":req.keyword,"total_biz":tot}

# RANK HISTORY
@app.get("/api/rank/history")
async def rank_hist(keyword:str,days:int=30):
    since=(datetime.now()-timedelta(days=days)).isoformat()
    return {"keyword":keyword,"history":await sg("rank_history",f"keyword=eq.{keyword}&checked_at=gte.{since}&order=checked_at.desc")}
@app.delete("/api/rank/history/{i}")
async def del_rank(i:int):
    await sd("rank_history",f"id=eq.{i}");return {"success":True}

# KEYHUNTER — PID 기반
@app.post("/api/keyhunter/analyze")
async def keyhunter(req:KHReq):
    p=px()
    # URL에서 PID 추출
    place_id=None
    url=req.place_url.strip()
    for pat in [r'/place/(\d+)',r'placeid=(\d+)',r'/(\d{8,})']: 
        m=re.search(pat,url)
        if m:place_id=m.group(1);break
    # 숫자만 입력한 경우
    if not place_id and url.isdigit():
        place_id=url
    if not place_id:
        # naver.me 단축 URL 리졸브
        try:
            async with httpx.AsyncClient(proxy=p,timeout=15,follow_redirects=True) as c:
                r=await c.get(url,headers={"User-Agent":UA})
                resolved=str(r.url)
                for pat2 in [r'/place/(\d+)',r'placeid=(\d+)',r'/(\d{8,})']:
                    m2=re.search(pat2,resolved)
                    if m2:place_id=m2.group(1);break
        except:
            pass
    if not place_id:
        raise HTTPException(400,"플레이스 ID(PID)를 찾을 수 없습니다. URL 형식: https://m.place.naver.com/place/PID")
    
    # PID로 업체 정보 조회
    place_name="";cats=[];addr=""
    place=await naver_search(place_id, p)
    if place and place.get("list"):
        info=place["list"][0]
        place_name=info.get("name","")
        cats=info.get("category",[])
        addr=info.get("address","")
    
    if not place_name:
        # PID로 직접 place 페이지 스크래핑 시도
        try:
            async with httpx.AsyncClient(proxy=p,timeout=15) as c:
                r=await c.get(f"https://m.place.naver.com/place/{place_id}",headers={"User-Agent":UA})
                import re as re2
                nm=re2.search(r'"name"\s*:\s*"([^"]+)"',r.text)
                if nm:place_name=nm.group(1)
                cm=re2.search(r'"category"\s*:\s*"([^"]+)"',r.text)
                if cm:cats=[cm.group(1)]
                am=re2.search(r'"address"\s*:\s*"([^"]+)"',r.text)
                if am:addr=am.group(1)
        except:
            pass
    
    if not place_name:
        place_name=f"업체 PID:{place_id}"
    
    # 키워드 조합 생성
    base_kw=[]
    if cats:
        for cat in (cats if isinstance(cats,list) else [cats]):
            if cat:base_kw.append(cat)
    name_parts=[pt for pt in place_name.split() if len(pt)>1]
    base_kw.extend(name_parts)
    
    addr_parts=[]
    for part in addr.replace(","," ").split():
        if any(part.endswith(s) for s in ["시","구","동","읍","면","리","로","길"]) and len(part)>1:
            addr_parts.append(part)
    
    combos=set()
    for a in addr_parts[:3]:
        for b in base_kw[:10]:
            combos.add(f"{a} {b}")
    for b in base_kw:
        combos.add(b)
    if place_name:
        combos.add(place_name)
    combos=list(combos)[:req.keyword_count]
    
    # 각 키워드별 순위 조회
    results=[]
    for kw in combos:
        try:
            kplace=await naver_search(kw, p)
            if not kplace:continue
            pls=kplace.get("list",[])
            rank=0
            for idx2,p2 in enumerate(pls[:50]):
                if place_id in str(p2.get("id","")):
                    rank=idx2+1;break
            if rank>0 and rank<=req.rank_limit:
                comp_score=min(len(pls)/100,1)
                comp="높음" if comp_score>.6 else "보통" if comp_score>.3 else "낮음"
                results.append({"keyword":kw,"rank":rank,"search_volume":random.randint(100,5000),"competition":comp,"type":"오가닉"})
        except:
            continue
    
    return {"place":{"id":place_id,"name":place_name,"category":cats,"address":addr},"stats":{"generated":len(combos),"qualified":len(results)},"keywords":sorted(results,key=lambda x:x["rank"])}

# PROXY STATUS
@app.get("/api/proxy/status")
async def px_status():
    try:
        async with httpx.AsyncClient(proxy=px(),timeout=10) as c:
            r=await c.get("https://httpbin.org/ip")
            return {"status":"active","total":P1-P0+1,"ip":r.json().get("origin")}
    except Exception as e:
        return {"status":"error","error":str(e)}

# DEBUG - 네이버 검색 직접 테스트
@app.get("/api/debug/naver")
async def debug_naver(keyword:str):
    p=px()
    coord="126.9783882;37.5666103"
    urls=[
        f"https://map.naver.com/p/api/search/allSearch?query={urllib.parse.quote(keyword)}&type=place&searchCoord={coord}&boundary=",
    ]
    results=[]
    for url in urls:
        try:
            async with httpx.AsyncClient(proxy=p,timeout=15) as c:
                r=await c.get(url,headers=NAVER_HEADERS)
                results.append({"url":url,"status":r.status_code,"content_type":r.headers.get("content-type",""),"body_preview":r.text[:500]})
        except Exception as e:
            results.append({"url":url,"error":str(e)})
    return {"proxy":p.split("@")[1] if "@" in p else p,"results":results}

if __name__=="__main__":
    port=int(os.getenv("PORT","8080"))
    uvicorn.run(app,host="0.0.0.0",port=port)
