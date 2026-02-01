import os
import time
import random
import logging
import json
import re
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from supabase import create_client

# =====================================================
# ✅ Load Configuration
# =====================================================
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

MODEL_NAME = "gemini-1.5-flash-latest"
TABLE_NAME = "jobs"

# =====================================================
# 🎨 Logging Configuration
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Hard Skills Database
HARD_SKILLS_DB = [
    "python", "sql", " r ", "java", "scala", "vba", "matlab", "c++", "sas",
    "power bi", "tableau", "excel",
    "aws", "azure", "gcp", "snowflake",
    "spark", "airflow", "etl",
    "machine learning", "nlp",
    "git", "statistics",
    "react", "next.js", "typescript", "node.js"
]

# =====================================================
# 🛠️ New Function: Search DB First
# =====================================================
def search_jobs_in_db(keyword: str, location: str):
    """
    Check Supabase for existing jobs matching criteria.
    Returns list of jobs or empty list.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 模糊查询: job_title 包含 keyword 且 location 包含 location
        # 按创建时间倒序 (最新的在前)
        response = supabase.table(TABLE_NAME).select("*")\
            .ilike("job_title", f"%{keyword}%")\
            .ilike("location", f"%{location}%")\
            .order("created_at", desc=True)\
            .limit(20)\
            .execute()
        
        data = response.data
        
        # ⚠️ 关键处理：把数据库里的 requirements 字符串转回列表
        for job in data:
            if isinstance(job.get("requirements"), str):
                try:
                    job["requirements"] = json.loads(job["requirements"])
                except:
                    job["requirements"] = []
                    
        return data

    except Exception as e:
        logging.error(f"⚠️ DB Search Error: {e}")
        return []

# =====================================================
# 🛠️ Gemini API Function
# =====================================================
def call_gemini_api(prompt):
    if not GOOGLE_API_KEY:
        logging.warning("⚠️  No Google API Key found")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 429:
            logging.error(f"❌ Gemini API Rate Limit (429)")
            return None
        
        if response.status_code != 200:
            logging.error(f"❌ Gemini API Error {response.status_code}: {response.text[:200]}")
            return None
            
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
        
    except Exception as e:
        logging.error(f"❌ Gemini Request Failed: {e}")
        return None

# =====================================================
# Helper Functions
# =====================================================
def scan_for_hard_skills(text: str) -> list:
    text = (text or "").lower()
    skills = set()
    for s in HARD_SKILLS_DB:
        if s == " r ":
            if " r " in text or "r language" in text: skills.add("R")
        elif s in text:
            skills.add(s.strip().title())
    return sorted(list(skills)) if skills else ["Check Job Description for details"]

def safe_json_load(text: str):
    if not text: return None
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    if text.endswith("```"): text = text[:-3]
    try:
        return json.loads(text)
    except:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try: return json.loads(text[start:end+1])
            except: pass
    return None

def extract_salary_from_text(text: str) -> str:
    if not text: return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    dollar_patterns = [
        r"\$\s?\d[\d,]*\s*(?:–|-)\s*\$?\s?\d[\d,]*(?:\s*(?:per\s*(?:year|annum)|p\.a|p\.d|per\s*day|per\s*hour|ph|hour|day|week|month))?.*",
        r"\$\s?\d[\d,]*(?:\s*(?:per\s*(?:year|annum)|p\.a|p\.d|per\s*day|per\s*hour|ph|hour|day|week|month))?.*",
    ]
    for ln in lines:
        if "$" in ln:
            for pat in dollar_patterns:
                if re.search(pat, ln): return ln
    return None

def infer_level_from_title(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ["intern", "internship"]): return "Intern"
    if any(k in t for k in ["graduate", "entry level", "junior", "jr"]): return "Junior"
    if any(k in t for k in ["mid", "intermediate", "associate"]): return "Mid"
    if any(k in t for k in ["senior", "sr", "experienced", "lead", "principal", "staff", "manager", "head"]): return "Senior"
    return "Unknown"

def infer_level_from_experience(jd: str) -> str:
    text = (jd or "").lower()
    matches = re.findall(r"(\d+)\s*\+?\s*years", text)
    if not matches: return "Unknown"
    years = max(int(x) for x in matches)
    if years <= 1: return "Junior"
    elif 2 <= years <= 3: return "Mid"
    else: return "Senior"

def final_level(level_from_ai, title, jd):
    if level_from_ai and level_from_ai != "Unknown": return level_from_ai
    lvl = infer_level_from_title(title)
    if lvl != "Unknown": return lvl
    return infer_level_from_experience(jd)

def get_company_from_detail_page(driver) -> str:
    selectors = ['[data-automation="job-detail-company"]', '[data-automation="advertiser-name"]']
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.text.strip(): return el.text.strip()
        except: continue
    return None

def get_work_type_from_detail_page(driver) -> str:
    try:
        el = driver.find_element(By.CSS_SELECTOR, '[data-automation="job-detail-work-type"]')
        if el.text.strip(): return el.text.strip()
    except: pass
    return "Unknown"

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    return driver

def safe_driver_get(driver, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get(url)
            return True
        except Exception:
            time.sleep(2)
    return False

# =====================================================
# 🚀 Core Logic
# =====================================================
def scrape_seek(keyword: str, location: str = "Australia", limit: int = 5):
    logging.info("="*70)
    logging.info(f"🚀 [SCRAPER START] Keyword: '{keyword}' | Location: '{location}' | Limit: {limit}")
    logging.info("="*70)
    
    jobs_data = []
    driver = None
    
    try:
        driver = create_driver()
        search_url = f"https://www.seek.com.au/jobs?keywords={keyword}&where={location}&sortmode=ListedDate"
        
        logging.info(f"🌐 Loading search page: {search_url}")
        if not safe_driver_get(driver, search_url):
            logging.error("❌ Failed to load search page")
            return []
            
        time.sleep(3)
        logging.info("✅ Search page loaded")

        # 1. Get Job List
        articles = driver.find_elements(By.TAG_NAME, "article")[:limit]
        job_links = []
        
        logging.info(f"📋 Extracting job cards...")
        for idx, card in enumerate(articles, 1):
            try:
                title_el = card.find_element(By.CSS_SELECTOR, '[data-automation="jobTitle"]')
                title = title_el.text.strip()
                href = title_el.get_attribute("href")
                
                salary_card = extract_salary_from_text(card.text)
                company_card = None
                try: company_card = card.find_element(By.CSS_SELECTOR, '[data-automation="jobCardCompanyName"]').text
                except: pass
                
                job_links.append((title, href, company_card, salary_card))
                logging.info(f"   [{idx}/{limit}] 📌 {title}")
            except: continue

        logging.info(f"✅ Found {len(job_links)} jobs to process\n")

        # 2. Process Details
        for idx, (title, url, comp_card, sal_card) in enumerate(job_links, 1):
            logging.info(f"🔍 [{idx}/{len(job_links)}] Processing: {title}")
            
            job_obj = {
                "job_title": title,
                "company": comp_card or "Private Advertiser",
                "salary": sal_card or "Not Specified",
                "location": location,
                "work_type": "Unknown",
                "level": "Unknown",
                "requirements": [],
                "url": url,
                "source": "NLP",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                driver.get(url)
                time.sleep(random.uniform(2, 4))
                
                try:
                    jd_el = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-automation="jobAdDetails"]')))
                    jd = jd_el.text
                except: jd = ""

                if job_obj["company"] == "Private Advertiser":
                    comp_detail = get_company_from_detail_page(driver)
                    if comp_detail: job_obj["company"] = comp_detail
                
                # Get work type
                work_type = get_work_type_from_detail_page(driver)
                if work_type != "Unknown":
                    job_obj["work_type"] = work_type
                    logging.info(f"   🕒 Work Type: {work_type}")

                # === AI Analysis ===
                ai_prompt = f"""
                You are a recruiter. Extract key requirements (bullets) from the text.
                Return valid JSON ONLY.
                Format: {{ "level": "Junior|Mid|Senior", "salary": "string", "requirements": ["bullet 1", "bullet 2"] }}
                JD: {jd[:4000]}
                """
                
                ai_text = call_gemini_api(ai_prompt)
                ai_data = safe_json_load(ai_text)
                
                if ai_data:
                    job_obj["level"] = ai_data.get("level", "Unknown")
                    reqs = ai_data.get("requirements", [])
                    if isinstance(reqs, list): job_obj["requirements"] = reqs
                    elif isinstance(reqs, str): job_obj["requirements"] = [reqs]
                    
                    if job_obj["salary"] == "Not Specified" and ai_data.get("salary"):
                        job_obj["salary"] = ai_data.get("salary")
                    job_obj["source"] = "AI"
                    logging.info(f"   ✅ AI analysis successful! (Source: AI)")
                else:
                    nlp_skills = scan_for_hard_skills(jd)
                    job_obj["requirements"] = nlp_skills
                    job_obj["source"] = "NLP"
                    logging.info(f"   ⚠️ AI failed, used NLP skills: {nlp_skills}")
                
                final_lvl = final_level(job_obj["level"], title, jd)
                job_obj["level"] = final_lvl
                
                jobs_data.append(job_obj)

            except Exception as e:
                logging.error(f"   ❌ Error: {e}")
                continue

        # 3. Save to Supabase
        if jobs_data and SUPABASE_URL and SUPABASE_KEY:
            try:
                supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                db_records = [{
                    "job_title": j["job_title"],
                    "company": j["company"],
                    "level": j["level"],
                    "salary": j["salary"],
                    "location": j["location"],
                    "work_type": j["work_type"],
                    "requirements": json.dumps(j["requirements"]),
                    "source": j["source"],
                    "url": j["url"]
                } for j in jobs_data]
                
                supabase.table(TABLE_NAME).upsert(db_records, on_conflict="url").execute()
                logging.info(f"💾 Database Sync: {len(jobs_data)} jobs saved.")
            except Exception as e:
                logging.error(f"❌ Supabase Error: {e}")

        logging.info(f"🎉 Process Complete: {len(jobs_data)} jobs\n")
        return jobs_data

    except Exception as e:
        logging.error(f"❌ Scraper Fatal Error: {e}")
        return []
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    # Test DB search
    print("Testing DB Search...")
    cached = search_jobs_in_db("data", "Perth")
    print(f"Found {len(cached)} cached jobs")
    print(json.dumps(cached, indent=2))