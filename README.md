# Job AutoApply Bot

Automatically applies to remote dev jobs and logs each application to Airtable and CSV.

---

### 1. Clone the GitHub Repo

Go to: https://github.com/jtorres-1  
Click “Use this template” or download the ZIP

---

### 2. Add Your Info

Open `config.json` and update:

{
  "full_name": "Your Name",
  "email": "you@example.com",
  "phone": "+1234567890",
  "keywords": ["developer", "remote", "python", "ai"],
  "resume_path": "resume.pdf"
}

3. Replace resume.pdf
Upload your own resume into the root folder and name it exactly: resume.pdf

4. Deploy to Railway
Go to https://railway.app
Click New Project → Deploy from GitHub Repo
Done ✅
It will auto-start and apply for jobs 24/7 in the background.
Check applied_jobs.csv or Airtable to view results.

5. Connect Airtable (Logging System)
Step 1: Create Airtable Token

Go to https://airtable.com/account → Create a token
Name it: JobBot
Scopes:
data.records:read
data.records:write
schema.bases:read
Select your workspace and base
Copy the token

Step 2: Get Your Base & Table IDs

Visit https://airtable.com/api
Click your base (e.g. “job bot logs”)
Copy:
Base ID → looks like appXXXXXXXXXXXX
Table ID → under "Table 1", looks like tblXXXXXXXXXXXX

Step 3: Add Environment Variables in Railway

Go to your Railway project → Variables tab, and add:

AIRTABLE_TOKEN = your_token_here
AIRTABLE_BASE_ID = your_base_id_here
AIRTABLE_TABLE_NAME = your_table_id_here
✅ Make sure the Time_stamp field in Airtable is set to Date with Time Enabled
(Otherwise logging will fail)

6. Done ✅
Bot applies to jobs on Remotive, RemoteOK, and WeWorkRemotely
Logs every successful apply to Airtable and CSV
No coding or manual effort required
Need help?
Email: jtxcode@yahoo.com

---

Let me know if you want me to drop this straight into your GitHub via a PR or if you’ll paste it yourself.
