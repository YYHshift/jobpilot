from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import Counter
from typing import Optional
import json
import ast
from scraper import scrape_seek, search_jobs_in_db, SUPABASE_URL, SUPABASE_KEY, TABLE_NAME
from supabase import create_client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    keyword: str
    location: str = "Australia"

@app.get("/")
def read_root():
    return {"status": "ok", "message": "JobPilot Backend is running"}

@app.get("/api/stats")
def get_stats(keyword: Optional[str] = None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"success": False, "error": "Database credentials missing"}
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 1. 查询数据
        query = supabase.table(TABLE_NAME).select("*") # 改为查所有字段
        if keyword:
            print(f"📊 Generating stats for: {keyword}")
            query = query.ilike("job_title", f"%{keyword}%")
        else:
            print(f"📊 Generating global stats")

        response = query.limit(1000).execute()
        data = response.data
        
        if not data:
            return {"success": True, "skills": [], "levels": [], "locations": [], "types": [], "total_jobs": 0}

        # --- 1. 统计技能 (Skills) ---
        all_skills = []
        for job in data:
            reqs = job.get("requirements")
            if reqs is None: continue
            
            parsed_list = []
            if isinstance(reqs, list):
                parsed_list = reqs
            elif isinstance(reqs, str):
                try:
                    parsed_list = json.loads(reqs)
                except:
                    try: parsed_list = ast.literal_eval(reqs)
                    except: pass
            
            if isinstance(parsed_list, list):
                cleaned = [str(r).strip().title() for r in parsed_list if r and str(r).lower() != "check job description for details"]
                all_skills.extend(cleaned)

        skill_counts = Counter(all_skills).most_common(10)
        formatted_skills = [{"name": k, "value": v} for k, v in skill_counts]

        # --- 2. 统计等级 (Level) ---
        all_levels = [job.get("level", "Unknown") for job in data]
        all_levels = [l for l in all_levels if l != "Unknown"]
        level_counts = Counter(all_levels)
        formatted_levels = [{"name": k, "value": v} for k, v in level_counts.items()]

        # --- 3. ✅ 新增：统计地点 (Location) ---
        all_locs = [job.get("location", "Unknown") for job in data]
        # 简单清洗：只取城市第一段 (e.g., "Perth WA" -> "Perth")
        cleaned_locs = []
        for loc in all_locs:
            if loc and loc != "Australia": # 排除泛指
                cleaned_locs.append(loc.split()[0].replace(',', ''))
        
        loc_counts = Counter(cleaned_locs).most_common(8) # 取前8个城市
        formatted_locs = [{"name": k, "value": v} for k, v in loc_counts]

        # --- 4. ✅ 新增：统计工作类型 (Work Type) ---
        all_types = [job.get("work_type", "Unknown") for job in data]
        all_types = [t for t in all_types if t != "Unknown"]
        type_counts = Counter(all_types)
        formatted_types = [{"name": k, "value": v} for k, v in type_counts.items()]

        return {
            "success": True, 
            "skills": formatted_skills, 
            "levels": formatted_levels,
            "locations": formatted_locs,
            "types": formatted_types,
            "total_jobs": len(data),
            "filter_keyword": keyword
        }

    except Exception as e:
        print(f"❌ Stats Error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/search")
def search_jobs(request: SearchRequest):
    # (保持不变)
    print(f"📥 Received search request: {request.keyword} in {request.location}")
    try:
        print("   🔍 Checking database cache...")
        cached_jobs = search_jobs_in_db(request.keyword, request.location)
        if cached_jobs and len(cached_jobs) > 0:
            print(f"   ✅ Cache HIT! Found {len(cached_jobs)} jobs in DB.")
            return {"success": True, "count": len(cached_jobs), "data": cached_jobs}
        print("   ⚠️ Cache MISS. Starting scraper...")
        jobs = scrape_seek(request.keyword, request.location, limit=20)
        return {"success": True, "count": len(jobs), "data": jobs}
    except Exception as e:
        return {"success": False, "error": str(e)}