"""
Seek职位爬虫 - 完整独立版本
功能: 从Seek.com.au爬取职位信息并上传到Supabase数据库

数据库表结构对应:
- job_title    -> 职位标题
- company      -> 公司名称  
- level        -> 职位级别 (Intern/Junior/Mid/Senior/Lead/Unknown)
- salary       -> 薪资信息
- location     -> 工作地点
- work_type    -> 工作类型 (Full-time/Part-time/Contract等)
- requirements -> 技能要求
- source       -> 数据来源 (AI/NLP)
- url          -> 职位链接 (唯一键)
"""

import os
import time
import random
import logging
import json
import re
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from google import genai
from supabase import create_client

# =====================================================
# ✅ 硬编码配置 - 请替换为你自己的值
# =====================================================
GOOGLE_API_KEY = "AIzaSyBTqyaxvOAnEvV7hG5XQ8Vcu1Oh_U783Uc"  # 替换为你的Gemini API密钥
SUPABASE_URL = "https://yxhxyrlmimuadynuezpg.supabase.co"      # 替换为你的Supabase URL (例如: https://xxx.supabase.co)
SUPABASE_KEY = "sb_publishable_gpEL3Ki-zpAfWiNV_wvyjQ_y4sFtGew"      # 替换为你的Supabase anon/public密钥

MODEL_NAME = "gemini-2.0-flash"  # Gemini模型
TABLE_NAME = "jobs"               # Supabase表名
MAX_RETRIES = 3                   # 连接失败最大重试次数
RETRY_DELAY = 5                   # 重试延迟(秒)
# =====================================================

# =====================================================
# Logging setup
# =====================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================
# 硬技能数据库 (用于NLP模式的技能提取)
# =====================================================
HARD_SKILLS_DB = [
    "python", "sql", " r ", "java", "scala", "vba", "matlab", "c++", "sas",
    "power bi", "tableau", "excel",
    "aws", "azure", "gcp", "snowflake",
    "spark", "airflow", "etl",
    "machine learning", "nlp",
    "git", "statistics"
]

# =====================================================
# Gemini client 初始化
# =====================================================
gemini_model = None
try:
    if GOOGLE_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError("请先替换 GOOGLE_API_KEY 为你的真实API密钥")

    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel(MODEL_NAME)
    logging.info(f"✅ Gemini model initialized: {MODEL_NAME}")
    list(genai.list_models())
except Exception as e:
    logging.warning(f"⚠️ Gemini unavailable, fallback to NLP mode: {e}")

# =====================================================
# 用户输入
# =====================================================
keyword_input = input("Enter job keyword: ").strip()
location_input = input("Enter location: ").strip() or "Australia"

jobs_data = []

# =====================================================
# 创建WebDriver函数
# =====================================================
def create_driver():
    """创建具有反检测功能的WebDriver实例"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 隐藏自动化特征
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    # 使用CDP命令隐藏webdriver属性
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


# =====================================================
# 辅助函数
# =====================================================
def clean(val):
    """将NaN转换为None (Supabase/Postgres兼容)"""
    if pd.isna(val):
        return None
    return val


def scan_for_hard_skills(text: str) -> str:
    """基于规则的NLP技能提取"""
    text = (text or "").lower()
    skills = set()
    for s in HARD_SKILLS_DB:
        if s == " r ":
            if " r " in text or "r language" in text:
                skills.add("R")
        elif s in text:
            skills.add(s.strip().title())
    return ", ".join(sorted(skills)) if skills else "Check JD"


def safe_json_load(text: str):
    """鲁棒的JSON解析器 (处理Gemini输出)"""
    if not text:
        return None

    text = text.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except:
        pass

    # 提取JSON对象
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except:
            return None

    return None


def extract_salary_from_text(text: str) -> str:
    """从职位卡片文本中提取薪资信息"""
    if not text:
        return None

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 优先匹配带美元符号的薪资
    dollar_patterns = [
        r"\$\s?\d[\d,]*\s*(?:–|-)\s*\$?\s?\d[\d,]*(?:\s*(?:per\s*(?:year|annum)|p\.a|p\.d|per\s*day|per\s*hour|ph|hour|day|week|month))?.*",
        r"\$\s?\d[\d,]*(?:\s*(?:per\s*(?:year|annum)|p\.a|p\.d|per\s*day|per\s*hour|ph|hour|day|week|month))?.*",
    ]

    for ln in lines:
        if "$" in ln:
            for pat in dollar_patterns:
                if re.search(pat, ln):
                    return ln

    # 匹配薪资相关关键词
    salary_keywords = [
        "competitive salary",
        "attractive salary",
        "attractive base salary",
        "salary range",
        "base salary",
        "great salary",
        "top $$$",
    ]

    for ln in lines:
        low = ln.lower()
        if any(k in low for k in salary_keywords):
            return ln

    return None


def infer_level_from_title(title: str) -> str:
    """从职位标题推断级别"""
    t = (title or "").lower()

    if any(k in t for k in ["intern", "internship"]):
        return "Intern"

    if any(k in t for k in ["graduate", "entry level", "entry-level", "junior", "jr"]):
        return "Junior"

    if any(k in t for k in ["mid", "intermediate", "associate"]):
        return "Mid"

    if any(k in t for k in ["senior", "sr", "experienced"]):
        return "Senior"

    if any(k in t for k in ["lead", "principal", "staff"]):
        return "Lead"

    if any(k in t for k in ["manager", "head", "director"]):
        return "Lead"

    return "Unknown"


def infer_level_from_experience(jd: str) -> str:
    """从工作描述中的工作年限推断级别"""
    text = (jd or "").lower()

    matches = re.findall(r"(\d+)\s*\+?\s*years", text)
    if not matches:
        matches = re.findall(r"(\d+)\s*\+?\s*yrs", text)

    if not matches:
        return "Unknown"

    years = max(int(x) for x in matches)

    if years <= 1:
        return "Junior"
    elif 2 <= years <= 3:
        return "Mid"
    elif 4 <= years <= 6:
        return "Senior"
    else:
        return "Lead"


def final_level(level_from_ai: str, title: str, jd: str) -> str:
    """最终级别判断优先级: AI > 标题 > JD年限"""
    if level_from_ai and level_from_ai != "Unknown":
        return level_from_ai

    lvl_title = infer_level_from_title(title)
    if lvl_title != "Unknown":
        return lvl_title

    return infer_level_from_experience(jd)


def get_company_from_detail_page(driver) -> str:
    """从详情页提取公司名称 (多选择器策略)"""
    selectors = [
        '[data-automation="job-detail-company"]',
        '[data-automation="advertiser-name"]',
        'a[data-automation="advertiser-name"]',
        'span[data-automation="advertiser-name"]',
        '[data-automation="companyProfileLink"]',
        'a[href*="/companies/"]',
    ]

    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            text = el.text.strip()
            if text:
                return text
        except:
            continue

    # 尝试从logo的alt属性提取
    try:
        logo = driver.find_element(By.CSS_SELECTOR, 'img[data-automation="job-company-logo"]')
        alt = logo.get_attribute("alt")
        if alt:
            return alt.strip()
    except:
        pass

    return None


def safe_driver_get(driver, url, max_retries=MAX_RETRIES):
    """安全导航到URL,带自动重试和WebDriver重建机制"""
    for attempt in range(max_retries):
        try:
            driver.get(url)
            return True
        except (WebDriverException, ConnectionResetError) as e:
            logging.warning(f"   ⚠️ Connection error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # 指数退避
                # 连接完全失败时重建WebDriver
                try:
                    driver.quit()
                except:
                    pass
                driver = create_driver()
            else:
                logging.error(f"   ❌ Failed to load {url} after {max_retries} attempts")
                return False
    return False


# =====================================================
# 主爬虫流程
# =====================================================
driver = None
try:
    driver = create_driver()
    
    search_url = (
        f"https://www.seek.com.au/jobs?"
        f"keywords={keyword_input.replace(' ', '%20')}"
        f"&where={location_input.replace(' ', '%20')}"
    )
    
    if not safe_driver_get(driver, search_url):
        logging.error("❌ Failed to load search page. Exiting.")
        exit(1)
    
    time.sleep(4)

    articles = driver.find_elements(By.TAG_NAME, "article")
    job_links = []

    # 第一步: 从列表页收集职位基本信息
    logging.info("📋 Collecting job listings from search page...")
    for card in articles:
        try:
            title_el = card.find_element(By.CSS_SELECTOR, '[data-automation="jobTitle"]')
            title = title_el.text.strip()
            href = title_el.get_attribute("href")

            company = None
            try:
                company_el = card.find_element(By.CSS_SELECTOR, '[data-automation="jobCardCompanyName"]')
                company = company_el.text.strip()
            except:
                company = None

            salary_from_card = extract_salary_from_text(card.text)

            job_links.append((title, href, company, salary_from_card))
        except:
            continue

    logging.info(f"🔍 Collected {len(job_links)} jobs\n")

    # 第二步: 访问每个职位详情页并提取完整信息
    for idx, (title, url, company_from_card, salary_from_card) in enumerate(job_links):
        logging.info(f"[{idx + 1}/{len(job_links)}] {title}")
        
        # 安全导航,带重试
        if not safe_driver_get(driver, url):
            logging.warning(f"   ⏭️ Skipping job due to connection error")
            continue
        
        time.sleep(random.uniform(3, 6))  # 随机延迟,避免检测

        # 提取职位描述
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-automation="jobAdDetails"]')
                )
            )
            jd = driver.find_element(
                By.CSS_SELECTOR,
                '[data-automation="jobAdDetails"]'
            ).text
        except TimeoutException:
            logging.warning(f"   ⏭️ Timeout waiting for job details, skipping")
            continue
        except Exception as e:
            logging.warning(f"   ⏭️ Error extracting JD: {e}, skipping")
            continue

        # 公司名称 (优先使用列表页的,降级到详情页)
        company_from_detail = get_company_from_detail_page(driver)
        company = company_from_card or company_from_detail or "Private Advertiser"

        # 工作类型
        try:
            work_type = driver.find_element(
                By.CSS_SELECTOR,
                '[data-automation="job-detail-work-type"]'
            ).text
        except:
            work_type = None

        # 薪资 (优先使用列表页提取的)
        salary = salary_from_card or "Not Specified"

        level = "Unknown"
        requirements = ""
        source = "NLP"  # 默认为NLP模式

        # 使用AI解析 或 降级到NLP
        if gemini_model:
            try:
                prompt = f"""
Return ONLY valid JSON. Do not add markdown. Do not add explanation.
Schema:
{{
  "job_level": "Intern|Junior|Mid|Senior|Lead|Unknown",
  "salary_extracted": "string",
  "requirements_summary": "string"
}}
Job Description:
{jd[:8000]}
"""
                response = gemini_model.generate_content(
                    model=MODEL_NAME,
                    contents=prompt
                )

                data = safe_json_load(getattr(response, "text", ""))

                if data:
                    level = data.get("job_level", level)

                    # 只在列表页没有薪资时才使用AI提取的
                    ai_salary = (data.get("salary_extracted") or "").strip()
                    if salary == "Not Specified" and ai_salary:
                        salary = ai_salary

                    requirements = data.get("requirements_summary", "")
                    source = "AI"
                    logging.info(f"   ✅ Parse Mode: AI ({MODEL_NAME})")
                else:
                    requirements = scan_for_hard_skills(jd)
                    source = "NLP"
                    logging.warning("   ⚠️ Parse Mode: NLP (BAD_JSON)")

                time.sleep(1.2)  # API调用间隔

            except Exception as e:
                requirements = scan_for_hard_skills(jd)
                source = "NLP"
                logging.error(f"   ⚠️ Parse Mode: NLP (AI_FAIL): {e}")
        else:
            # Gemini不可用,使用NLP模式
            requirements = scan_for_hard_skills(jd)
            source = "NLP"
            logging.info("   📝 Parse Mode: NLP")

        # 最终级别判断 (AI > 标题 > JD年限)
        level = final_level(level, title, jd)

        # 添加到结果列表
        jobs_data.append({
            "Job_Title": title,
            "Company": company,
            "Level": level,
            "Salary": salary,
            "Location": location_input,
            "Work_Type": work_type,
            "Requirements": requirements,
            "Source": source,
            "URL": url
        })
        
        # 每5个职位记录一次进度
        if (idx + 1) % 5 == 0:
            logging.info(f"   💾 Progress: {len(jobs_data)} jobs collected so far")

except KeyboardInterrupt:
    logging.info("\n⚠️ Process interrupted by user (Ctrl+C). Saving collected data...")
except Exception as e:
    logging.error(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        try:
            driver.quit()
            logging.info("🔌 Browser closed")
        except:
            pass

# =====================================================
# 保存CSV文件 (本地备份)
# =====================================================
if jobs_data:
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = f"seek_{keyword_input.replace(' ', '_')}_Requirements.csv"
    csv_file = os.path.join(script_dir, csv_filename)
    
    df_output = pd.DataFrame(jobs_data)
    df_output.to_csv(csv_file, index=False, encoding="utf-8-sig")
    logging.info(f"\n✅ CSV saved: {csv_file} ({len(jobs_data)} jobs)")
else:
    logging.warning("⚠️ No job data collected to save to CSV.")

# =====================================================
# 上传到Supabase数据库
# =====================================================
if jobs_data:
    logging.info("\n📡 Uploading to Supabase...")

    try:
        # 验证配置
        if SUPABASE_URL == "YOUR_SUPABASE_URL_HERE" or SUPABASE_KEY == "YOUR_SUPABASE_KEY_HERE":
            raise ValueError("请先替换 SUPABASE_URL 和 SUPABASE_KEY 为你的真实值")

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        df_for_supabase = pd.DataFrame(jobs_data)

        db_records = []

        # 转换为Supabase记录格式 (字段名完全对应数据库表结构)
        for _, row in df_for_supabase.iterrows():
            company_val = clean(row.get("Company")) or "Private Advertiser"

            db_records.append({
                "job_title": clean(row.get("Job_Title")),      # → jobs.job_title
                "company": company_val,                         # → jobs.company
                "level": clean(row.get("Level")),              # → jobs.level
                "salary": clean(row.get("Salary")),            # → jobs.salary
                "location": clean(row.get("Location")),        # → jobs.location
                "work_type": clean(row.get("Work_Type")),      # → jobs.work_type
                "requirements": clean(row.get("Requirements")),# → jobs.requirements
                "source": clean(row.get("Source")),            # → jobs.source
                "url": clean(row.get("URL")),                  # → jobs.url (UNIQUE)
            })

        if db_records:
            logging.info(f"🧪 Sample record: {db_records[0]}")

        # 使用upsert: 如果URL已存在则更新,否则插入
        supabase.table(TABLE_NAME).upsert(
            db_records,
            on_conflict="url"  # 基于URL的唯一约束
        ).execute()

        logging.info(f"🎉 Successfully uploaded {len(db_records)} jobs to Supabase!")
        logging.info(f"   Table: {TABLE_NAME}")
        logging.info(f"   Strategy: upsert (insert or update based on URL)")
        
    except Exception as e:
        logging.error(f"❌ Supabase upload failed: {e}")
        logging.info("💾 Data has been saved to CSV file as backup")
else:
    logging.warning("⚠️ No job data to upload to Supabase.")

logging.info("\n✨ Process completed!")