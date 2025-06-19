# Full main.py - Job AutoApply Bot
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

app = Flask(__name__)

@app.route("/")
def home():
    return "alive"

CONFIG_FILE = "config.json"
with open(CONFIG_FILE) as f:
    config = json.load(f)

KEYWORDS = [kw.lower() for kw in config.get("keywords", [])]
MAX_RESULTS = config.get("max_results", 50)
RESUME_PATH = config.get("resume_path", "resume.pdf")
USER_DATA = config.get("user_data", {})
CSV_PATH = "applied_jobs.csv"

def load_applied_urls():
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        return {row[3] for row in reader if len(row) >= 4}

def log_application(job):
    is_new = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "title", "company", "url"])
        row = [
            datetime.datetime.utcnow().isoformat(),
            job["title"],
            job["company"],
            job["url"]
        ]
        writer.writerow(row)
    print(f"[CSV LOG] {','.join(row)}", flush=True)
    print(f"[LOG] Applied → {job['url']}", flush=True)

# Add scrapers here (Remotive, RemoteOK, WWR, Jobspresso, etc.)...
# ... YOUR EXISTING SCRAPER FUNCTIONS ARE GOOD

def get_jobs():
    scrapers = [
        scrape_remotive,
        scrape_remoteok,
        scrape_weworkremotely,
        scrape_jobspresso
    ]
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
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(job["url"])
        time.sleep(4)
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for i in inputs:
            name = i.get_attribute("name")
            if name and "email" in name.lower():
                i.send_keys(USER_DATA.get("email", ""))
            elif name and "name" in name.lower():
                i.send_keys(USER_DATA.get("full_name", ""))
            elif name and "phone" in name.lower():
                i.send_keys(USER_DATA.get("phone", ""))

        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        for f in file_inputs:
            f.send_keys(os.path.abspath(RESUME_PATH))

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "submit" in b.text.lower() or "apply" in b.text.lower():
                b.click()
                break
        print("[AUTO] Applied successfully")
        log_application(job)
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
        print(f"[APPLY] {job['url']}")
        apply_to_job(job)
        applied.add(job["url"])
    print("[BOT] Cycle complete")

def scheduler():
    bot_cycle()
    while True:
        time.sleep(30 * 60)  # Every 30 mins
        bot_cycle()

if __name__ == "__main__":
    th = threading.Thread(target=scheduler, daemon=True)
    th.start()
    print("[MAIN] Scheduler thread started")
    app.run(host="0.0.0.0", port=3000)
