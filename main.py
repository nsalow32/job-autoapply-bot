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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

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

def load_applied_urls():
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH) as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        return {row[3] for row in reader if len(row) >= 4}


def log_application(job):
    row = [
        datetime.datetime.utcnow().isoformat(),
        job["title"],
        job["company"],
        job["url"]
    ]
    print(f"[CSV LOG] {','.join(row)}", flush=True)
    print(f"[LOG] Applied → {job['url']}", flush=True)



# --- SCRAPERS ---

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
            if not (t and l):
                continue
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
            if not l:
                continue
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
    print("[SCRAPE] We Work Remotely...")
    url = "https://weworkremotely.com/categories/remote-programming-jobs"
    jobs = []
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for section in soup.select("section.jobs li.feature")[:MAX_RESULTS]:
            l = section.select_one("a")
            if not l:
                continue
            href = l["href"]
            full_url = "https://weworkremotely.com" + href
            title = section.get_text(strip=True)
            company = "Unknown"
            if any(kw in title.lower() for kw in KEYWORDS):
                jobs.append({"url": full_url, "title": title, "company": company})
    except Exception as e:
        print(f"[ERROR] WWR: {e}")
    return jobs

def scrape_jobspresso():
    print("[SCRAPE] Jobspresso...")
    url = "https://jobspresso.co/remote-tech-jobs/"
    jobs = []
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for post in soup.select("article.job_listing")[:MAX_RESULTS]:
            title_el = post.select_one("h3")
            company_el = post.select_one("div.company")
            link_el = post.select_one("a")
            if title_el and link_el:
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                href = link_el["href"]
                if any(kw in (title + company).lower() for kw in KEYWORDS):
                    jobs.append({"url": href, "title": title, "company": company})
    except Exception as e:
        print(f"[ERROR] Jobspresso: {e}")
    return jobs

def scrape_otta():
    print("[SCRAPE] Otta...")
    return []

def scrape_angellist():
    print("[SCRAPE] AngelList...")
    return []

def get_jobs():
    scrapers = [
        scrape_remotive,
        scrape_remoteok,
        scrape_weworkremotely,
        scrape_jobspresso,
        scrape_otta,
        scrape_angellist
    ]
    all_jobs = []
    for fn in scrapers:
        all_jobs.extend(fn())

    seen, unique = set(), []
    for j in all_jobs:
        u = j["url"]
        if u not in seen:
            seen.add(u)
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
        u = job["url"]
        if u in applied:
            print(f"⏩ Skipping {u}")
            continue

        print(f"[APPLY] {u}")
        apply_to_job(job)
        log_application(job)
        applied.add(u)

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
