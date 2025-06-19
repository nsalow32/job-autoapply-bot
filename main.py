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
from urllib.parse import quote  # ← use quote, not quote_plus

app = Flask(__name__)

@app.route("/")
def home():
    return "alive"

# Load config
CONFIG_FILE = "config.json"
with open(CONFIG_FILE) as f:
    config = json.load(f)

KEYWORDS = [kw.lower() for kw in config.get("keywords", [])]
MAX_RESULTS = config.get("max_results", 50)
RESUME_PATH = config.get("resume_path", "resume.pdf")
USER_DATA = config.get("user_data", {})
CSV_PATH = "applied_jobs.csv"

# Airtable ENV
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

def load_applied_urls():
    # initialize CSV with header row if missing
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "title", "company", "url"])
        return set()
    # else read existing
    with open(CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return {row[3] for row in reader if len(row) >= 4}

def log_application(job):
    ts = datetime.datetime.utcnow().isoformat()
    row = [ts, job["title"], job["company"], job["url"]]

    # append to CSV
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)
    print(f"[CSV LOG] {','.join(row)}", flush=True)
    print(f"[LOG] Applied → {job['url']}", flush=True)

    # post to Airtable
    try:
        table = quote(AIRTABLE_TABLE_NAME, safe="")   # encode spaces as %20
        airtable_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "fields": {
                "Time_stamp": ts,
                "Title": job["title"],
                "Company": job["company"],
                "URL": job["url"]
            }
        }
        r = requests.post(airtable_url, headers=headers, json=payload, timeout=10)
        if r.status_code in (200, 201):
            print("[AIRTABLE ✅] Log synced.", flush=True)
        else:
            print(f"[AIRTABLE ERROR] {r.status_code}: {r.text}", flush=True)
    except Exception as e:
        print(f"[AIRTABLE ERROR] {e}", flush=True)

def scrape_remotive():
    print("[SCRAPE] Remotive...")
    url = "https://remotive.io/remote-jobs/software-dev"
    jobs = []
    try:
        r = requests.get(url, timeout=10)
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
            text = (title + " " + company).lower()
            if any(kw in text for kw in KEYWORDS):
                jobs.append({"url": full, "title": title, "company": company})
    except Exception as e:
        print(f"[ERROR] Remotive: {e}")
    return jobs

def scrape_remoteok():
    print("[SCRAPE] RemoteOK...")
    url = "https://remoteok.io/remote-dev-jobs"
    jobs = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("tr.job")[:MAX_RESULTS]:
            l = row.select_one("a.preventLink")
            if not l: continue
            full_url = "https://remoteok.io" + l["href"]
            title = row.get("data-position", "Remote Job")
            company = row.get("data-company", "Unknown")
            text = (title + " " + company).lower()
            if any(kw in text for kw in KEYWORDS):
                jobs.append({"url": full_url, "title": title, "company": company})
    except Exception as e:
        print(f"[ERROR] RemoteOK: {e}")
    return jobs

def scrape_weworkremotely():
    print("[SCRAPE] WeWorkRemotely...")
    url = "https://weworkremotely.com/categories/remote-programming-jobs"
    jobs = []
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for section in soup.select("section.jobs li.feature")[:MAX_RESULTS]:
            l = section.select_one("a")
            if not l: continue
            href = l["href"]
            full_url = "https://weworkremotely.com" + href
            title = section.get_text(strip=True)
            if any(kw in title.lower() for kw in KEYWORDS):
                jobs.append({"url": full_url, "title": title, "company": "Unknown"})
    except Exception as e:
        print(f"[ERROR] WWR: {e}")
    return jobs

def get_jobs():
    scrapers = [scrape_remotive, scrape_remoteok, scrape_weworkremotely]
    all_jobs = []
    for fn in scrapers:
        all_jobs.extend(fn())
    seen, unique = set(), []
    for j in all_jobs:
        if j["url"] not in seen:
            seen.add(j["url"])
            unique.append(j)
        if len(unique) >= MAX_RESULTS:
            break
    print(f"[SCRAPE] {len(unique)} unique jobs found")
    return unique

def apply_to_job(job):
    print(f"[AUTO] Attempting real apply to {job['url']}")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(job["url"])
        time.sleep(4)
        # fill inputs
        for i in driver.find_elements(By.TAG_NAME, "input"):
            name = i.get_attribute("name") or ""
            if "email" in name.lower():   i.send_keys(USER_DATA.get("email", ""))
            elif "name" in name.lower():  i.send_keys(USER_DATA.get("full_name", ""))
            elif "phone" in name.lower(): i.send_keys(USER_DATA.get("phone", ""))
        # upload resume
        for f in driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            f.send_keys(os.path.abspath(RESUME_PATH))
        # click apply
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if "submit" in b.text.lower() or "apply" in b.text.lower():
                b.click()
                break
        print("[AUTO] Applied successfully")
    except Exception as e:
        print(f"[ERROR][AUTO] Failed to apply: {e}")
    finally:
        driver.quit()

def bot_cycle():
    applied = load_applied_urls()
    print(f"[BOT] Loaded {len(applied)} applied URLs")
    jobs = get_jobs()
    print(f"[BOT] Fetched {len(jobs)} jobs")
    for job in jobs:
        if job["url"] in applied:
            print(f"⏩ Skipping {job['url']}")
            continue
        apply_to_job(job)
        log_application(job)
        applied.add(job["url"])
    print("[BOT] Cycle complete")

def scheduler():
    bot_cycle()
    while True:
        time.sleep(30)
        bot_cycle()

if __name__ == "__main__":
    th = threading.Thread(target=scheduler, daemon=True)
    th.start()
    print("[MAIN] Scheduler thread started")
    app.run(host="0.0.0.0", port=3000)
