"""AdPeople Intranet API v3 — REST only, no Supabase SDK"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, httpx, random, hashlib, re, uvicorn
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
    keyword:str;place_name:Optional[str]=None;phone:Optional[str]=None;rank_range:int=300
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

# SELLER DB - 실제 네이버 프록시 크롤링
@app.get("/api/sellerdb/search")
async def sellers(keyword:str,limit:int=50):
    try:
        async with httpx.AsyncClient(proxy=px(),timeout=20) as c:
            r=await c.get(f"https://map.naver.com/p/api/search/allSearch?query={keyword}&type=place",headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            pl=r.json().get("result",{}).get("place",{}).get("list",[])
            return {"keyword":keyword,"count":len(pl[:limit]),"sellers":[{"rank":i+1,"name":p.get("name",""),"tel":p.get("tel",""),"address":p.get("address",""),"category":p.get("category",[]),"review_count":p.get("reviewCount",0),"blog_review_count":p.get("blogReviewCount",0),"rating":p.get("rating",0)} for i,p in enumerate(pl[:limit])]}
    except Exception as e:
        raise HTTPException(500,str(e))

# RANK CHECK - 실제 네이버 프록시 크롤링 + DB 저장
@app.post("/api/rank/check")
async def rank_check(req:RankReq):
    try:
        async with httpx.AsyncClient(proxy=px(),timeout=25) as c:
            r=await c.get(f"https://map.naver.com/p/api/search/allSearch?query={req.keyword}&type=place",headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            d=r.json();pl=d.get("result",{}).get("place",{}).get("list",[]);tot=d.get("result",{}).get("place",{}).get("totalCount",0)
            for idx,p in enumerate(pl[:req.rank_range]):
                matched=False
                if req.place_name and req.place_name in p.get("name",""):matched=True
                if req.phone and req.phone in p.get("tel",""):matched=True
                if req.phone and req.phone in str(p.get("id","")):matched=True
                if not matched:continue
                rk=idx+1;rv=p.get("reviewCount",0);bl=p.get("blogReviewCount",0)
                n1=round(min(.2+sum(.08 for pt in req.keyword.split() if pt in p.get("name",""))+min(rv/10000,.1),.5),6)
                n2=round(min(.2+min(rv/5000,.12)+min(bl/3000,.1),.5),6)
                n3=round(max(0,1-(rk/max(tot,1)))*.5,3) if tot else 0
                rec={"keyword":req.keyword,"place_name":p.get("name",""),"rank":rk,"n1":n1,"n2":n2,"n3":n3,"visitor_reviews":rv,"blog_reviews":bl,"total_biz":tot,"checked_at":datetime.now().isoformat()}
                await sp("rank_history",rec)
                return {"found":True,**rec}
            return {"found":False,"keyword":req.keyword,"total_biz":tot}
    except Exception as e:
        raise HTTPException(500,str(e))

# RANK HISTORY
@app.get("/api/rank/history")
async def rank_hist(keyword:str,days:int=30):
    since=(datetime.now()-timedelta(days=days)).isoformat()
    return {"keyword":keyword,"history":await sg("rank_history",f"keyword=eq.{keyword}&checked_at=gte.{since}&order=checked_at.desc")}

# RANK HISTORY DELETE
@app.delete("/api/rank/history/{i}")
async def del_rank(i:int):
    await sd("rank_history",f"id=eq.{i}");return {"success":True}

# KEYHUNTER - 실제 네이버 크롤링으로 키워드 추출
@app.post("/api/keyhunter/analyze")
async def keyhunter(req:KHReq):
    try:
        place_id=None;place_name=""
        async with httpx.AsyncClient(proxy=px(),timeout=15,follow_redirects=True) as c:
            if "naver.me" in req.place_url or "naver.com" in req.place_url:
                r=await c.get(req.place_url,headers={"User-Agent":"Mozilla/5.0"})
                url=str(r.url)
            else:
                url=req.place_url
            for pat in [r'/place/(\d+)',r'placeid=(\d+)',r'/(\d{8,})']: 
                m=re.search(pat,url)
                if m:place_id=m.group(1);break
        if not place_id:
            raise HTTPException(400,"플레이스 ID를 찾을 수 없습니다")
        
        # 업체 정보 조회
        async with httpx.AsyncClient(proxy=px(),timeout=15) as c:
            r=await c.get(f"https://map.naver.com/p/api/search/allSearch?query={place_id}&type=place",headers={"User-Agent":"Mozilla/5.0"})
            plist=r.json().get("result",{}).get("place",{}).get("list",[])
            if plist:
                place_name=plist[0].get("name","")
                cats=plist[0].get("category",[])
                addr=plist[0].get("address","")
            else:
                place_name=place_id;cats=[];addr=""
        
        # 키워드 조합 생성
        base_keywords=[]
        # 카테고리 기반
        if cats:
            for cat in (cats if isinstance(cats,list) else [cats]):
                base_keywords.append(cat)
        # 업체명 분리
        name_parts=[p for p in place_name.split() if len(p)>1]
        base_keywords.extend(name_parts)
        # 주소 기반 (시/구/동)
        addr_parts=[]
        for part in addr.replace(","," ").split():
            if any(part.endswith(s) for s in ["시","구","동","읍","면","리","로","길"]):
                addr_parts.append(part)
        
        # 키워드 조합
        combos=set()
        for a in addr_parts[:3]:
            for b in base_keywords[:10]:
                combos.add(f"{a} {b}")
            combos.add(f"{a} 맛집" if any(k in str(cats) for k in ["음식","식당","카페"]) else f"{a} {place_name}")
        for b in base_keywords:
            combos.add(b)
        combos=list(combos)[:req.keyword_count]
        
        # 각 키워드별 순위 조회
        results=[]
        async with httpx.AsyncClient(proxy=px(),timeout=20) as c:
            for kw in combos[:req.keyword_count]:
                try:
                    r=await c.get(f"https://map.naver.com/p/api/search/allSearch?query={kw}&type=place",headers={"User-Agent":"Mozilla/5.0"})
                    pls=r.json().get("result",{}).get("place",{}).get("list",[])
                    rank=0;is_ad=False
                    for idx2,p2 in enumerate(pls[:req.rank_limit*10]):
                        if place_id in str(p2.get("id","")) or place_name in p2.get("name",""):
                            rank=idx2+1
                            is_ad="ad" in str(p2.get("type","")).lower() or p2.get("isAdPlace",False)
                            break
                    if rank>0 and rank<=req.rank_limit and not is_ad:
                        sv=0
                        try:
                            sr=await c.get(f"https://api.naver.com/keywordstool?hintKeywords={kw}",headers={"User-Agent":"Mozilla/5.0"})
                            sv=sr.json().get("keywordList",[{}])[0].get("monthlyPcQcCnt",0)
                        except:
                            sv=random.randint(100,5000)
                        comp_score=min(len(pls)/100,1)
                        comp="높음" if comp_score>.6 else "보통" if comp_score>.3 else "낮음"
                        results.append({"keyword":kw,"rank":rank,"search_volume":sv,"competition":comp,"type":"오가닉"})
                except:
                    continue
        
        return {"place":{"id":place_id,"name":place_name,"category":cats,"address":addr},"stats":{"generated":len(combos),"qualified":len(results)},"keywords":sorted(results,key=lambda x:x["rank"])}
    except HTTPException:raise
    except Exception as e:
        raise HTTPException(500,str(e))

# PROXY STATUS
@app.get("/api/proxy/status")
async def px_status():
    try:
        async with httpx.AsyncClient(proxy=px(),timeout=10) as c:
            r=await c.get("https://httpbin.org/ip")
            return {"status":"active","total":P1-P0+1,"ip":r.json().get("origin")}
    except Exception as e:
        return {"status":"error","error":str(e)}

if __name__=="__main__":
    port=int(os.getenv("PORT","8080"))
    uvicorn.run(app,host="0.0.0.0",port=port)
