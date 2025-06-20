import os
import time
import csv
import json
import datetime
import threading
import requests
from flask import Flask
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pyairtable import Table   # new Airtable client

print("[DEBUG] AIRTABLE_TOKEN =", os.getenv("AIRTABLE_TOKEN"))
print("[DEBUG] AIRTABLE_BASE_ID =", os.getenv("AIRTABLE_BASE_ID"))
print("[DEBUG] AIRTABLE_TABLE_NAME =", os.getenv("AIRTABLE_TABLE_NAME"))


app = Flask(__name__)

@app.route("/")
def home():
    return "alive"

# Load config
CONFIG_FILE = "config.json"
with open(CONFIG_FILE) as f:
    config = json.load(f)

KEYWORDS    = [kw.lower() for kw in config.get("keywords", [])]
MAX_RESULTS = config.get("max_results", 50)
RESUME_PATH = config.get("resume_path", "resume.pdf")
USER_DATA   = config.get("user_data", {})
CSV_PATH    = "applied_jobs.csv"

# Airtable ENV + client
AIRTABLE_TOKEN      = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID    = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
airtable = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def load_applied_urls():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "title", "company", "url"])
        return set()
    with open(CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return {row[3] for row in reader if len(row) >= 4}

def log_application(job):
    ts  = datetime.datetime.utcnow().isoformat()
    row = [ts, job["title"], job["company"], job["url"]]

    # 1) Append CSV
    with open(CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerow(row)
    print(f"[CSV LOG] {','.join(row)}", flush=True)
    print(f"[LOG] Applied → {job['url']}", flush=True)

    # 2) Airtable record
    try:
        rec = airtable.create({
            "Time_stamp": ts,
            "Title":      job["title"],
            "Company":    job["company"],
            "URL":        job["url"]
        })
        print(f"[AIRTABLE ✅] Logged as {rec['id']}", flush=True)
    except Exception as e:
        print(f"[AIRTABLE ERROR] {e}", flush=True)

def location_allowed(text):
    raw = config.get("location_filter", "")
    if not raw.strip():
        return True  # No filter = allow everything

    locs = [loc.strip().lower() for loc in raw.split(",") if loc.strip()]
    text = text.lower()

    for loc in locs:
        if loc in text:
            return True

    return False



def scrape_remotive():
    print("[SCRAPE] Remotive...", flush=True)
    url  = "https://remotive.io/remote-jobs/software-dev"
    jobs = []
    try:
        r = requests.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for tile in soup.select("div.job-tile")[:MAX_RESULTS]:
            t = tile.select_one(".job-tile-title")
            l = tile.select_one("a")
            c = tile.select_one(".job-tile-company")
            if not (t and l): continue
            title = t.get_text(strip=True)
            company = c.get_text(strip=True) if c else "Unknown"
            href = l["href"]
            full = href if href.startswith("http") else f"https://remotive.io{href}"
            text = (title + " " + company + " " + full).lower()
            if any(kw in text for kw in KEYWORDS) and location_allowed(text):
                jobs.append({"url": full, "title": title, "company": company})
    except Exception as e:
        print(f"[ERROR] Remotive: {e}", flush=True)
    return jobs

def scrape_remoteok():
    print("[SCRAPE] RemoteOK...", flush=True)
    url = "https://remoteok.io/remote-dev-jobs"
    jobs = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("tr.job")[:MAX_RESULTS]:
            l = row.select_one("a.preventLink")
            if not l: continue
            full_url = "https://remoteok.io" + l["href"]
            title = row.get("data-position", "Remote Job")
            company = row.get("data-company", "Unknown")
            text = (title + " " + company + " " + full_url).lower()
            if any(kw in text for kw in KEYWORDS) and location_allowed(text):
                jobs.append({"url": full_url, "title": title, "company": company})
    except Exception as e:
        print(f"[ERROR] RemoteOK: {e}", flush=True)
    return jobs

def scrape_weworkremotely():
    print("[SCRAPE] WeWorkRemotely...", flush=True)
    url = "https://weworkremotely.com/categories/remote-programming-jobs"
    jobs = []
    try:
        r = requests.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for sec in soup.select("section.jobs li.feature")[:MAX_RESULTS]:
            l = sec.select_one("a")
            if not l: continue
            href = l["href"]
            full_url = "https://weworkremotely.com" + href
            title = sec.get_text(strip=True)
            text = (title + " " + full_url).lower()
            if any(kw in title.lower() for kw in KEYWORDS) and location_allowed(text):
                jobs.append({"url": full_url, "title": title, "company": "Unknown"})
    except Exception as e:
        print(f"[ERROR] WWR: {e}", flush=True)
    return jobs

def scrape_jobspresso():
    print("[SCRAPE] Jobspresso...", flush=True)
    url = "https://jobspresso.co/remote-developer-jobs/"
    jobs = []
    try:
        r = requests.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for li in soup.select("ul.jobs li.job_listing")[:MAX_RESULTS]:
            a = li.select_one("a")
            if not a: continue
            href = a["href"]
            title = a.get("title", "Remote Job")
            company = li.select_one(".company")
            company_name = company.get_text(strip=True) if company else "Unknown"
            text = (title + " " + company_name + " " + href).lower()
            if any(kw in title.lower() for kw in KEYWORDS) and location_allowed(text):
                jobs.append({"url": href, "title": title, "company": company_name})
    except Exception as e:
        print(f"[ERROR] Jobspresso: {e}", flush=True)
    return jobs

def scrape_remoteco():
    print("[SCRAPE] Remote.co...", flush=True)
    url = "https://remote.co/remote-jobs/developer/"
    jobs = []
    try:
        r = requests.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("li.job_listing")[:MAX_RESULTS]:
            a = row.select_one("a")
            if not a: continue
            href = a["href"]
            title = a.get("title", "Remote Job")
            company = row.select_one(".company")
            company_name = company.get_text(strip=True) if company else "Unknown"
            text = (title + " " + company_name + " " + href).lower()
            if any(kw in title.lower() for kw in KEYWORDS) and location_allowed(text):
                jobs.append({"url": href, "title": title, "company": company_name})
    except Exception as e:
        print(f"[ERROR] Remote.co: {e}", flush=True)
    return jobs



def get_jobs():
    all_jobs = []
    for fn in (scrape_remotive, scrape_remoteok, scrape_weworkremotely, scrape_jobspresso, scrape_remoteco):
        try:
            jobs = fn()
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[SCRAPE ERROR] {fn.__name__}: {e}", flush=True)
        time.sleep(3)  # Delay between scrapers to reduce timeout risk

    seen, unique = set(), []
    for j in all_jobs:
        if j["url"] not in seen:
            seen.add(j["url"])
            unique.append(j)
        if len(unique) >= MAX_RESULTS:
            break

    print(f"[SCRAPE] {len(unique)} unique jobs found", flush=True)
    return unique


def apply_to_job(job):
    print(f"[AUTO] Applying → {job['url']}", flush=True)
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(job["url"])
        time.sleep(4)
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            name = inp.get_attribute("name") or ""
            if "email" in name.lower():
                inp.send_keys(USER_DATA.get("email",""))
            elif "name" in name.lower():
                inp.send_keys(USER_DATA.get("full_name",""))
            elif "phone" in name.lower():
                inp.send_keys(USER_DATA.get("phone",""))
        for f in driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            f.send_keys(os.path.abspath(RESUME_PATH))
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            t = btn.text.lower()
            if "submit" in t or "apply" in t:
                btn.click()
                break
        print("[AUTO] Success", flush=True)
    except Exception as e:
        print(f"[AUTO ERROR] {e}", flush=True)
    finally:
        driver.quit()

def bot_cycle():
    applied = load_applied_urls()
    print(f"[BOT] {len(applied)} URLs loaded", flush=True)
    jobs = get_jobs()
    print(f"[BOT] {len(jobs)} jobs fetched", flush=True)
    for job in jobs:
        if job["url"] in applied:
            print(f"[BOT] Skipping {job['url']}", flush=True)
            continue
        apply_to_job(job)
        log_application(job)
        applied.add(job["url"])
    print("[BOT] Cycle complete", flush=True)

def scheduler():
    bot_cycle()
    while True:
        time.sleep(30)
        bot_cycle()

if __name__ == "__main__":
    th = threading.Thread(target=scheduler, daemon=True)
    th.start()
    print("[MAIN] Scheduler started", flush=True)
    app.run(host="0.0.0.0", port=3000)
