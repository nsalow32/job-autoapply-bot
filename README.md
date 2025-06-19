# Job AutoApply Bot

Automatically applies to remote dev jobs and logs each application to **Airtable** and **CSV** — 24/7.

---

## 1. Clone the GitHub Repo

Go to: [https://github.com/jtorres-1](https://github.com/jtorres-1)  
Click **“Use this template”** or download the ZIP. OR CLICK GREEN CODE BUTTON AND COPY TEMPLATE

---

## 2. Add Your Info

Open `config.json` and update:


{
  "full_name": "Your Name",
  "email": "you@example.com",
  "phone": "+1234567890",
  "keywords": ["developer", "remote", "python", "ai"],
  "resume_path": "resume.pdf"
}

3. Replace Your Resume

Upload your resume into the root folder and rename it exactly:
resume.pdf

4. Connect Airtable (Logging System)

Step 1: Create a Token
Go to: https://airtable.com/account
Click “Create token”
Name it: JobBot
Select these Scopes:
data.records:read
data.records:write
schema.bases:read
Under Access, select:
Your workspace
The base you're using for logging (e.g. “job bot logs”)
Click Create token and Copy it

Step 2: Get Your Base ID and Table ID
Go to: https://airtable.com/api
Click your base (e.g. “job bot logs”)
Copy these:
Base ID → starts with app...
Table ID (under Table 1) → starts with tbl...

AIRTABLE_TOKEN      = your_token_here
AIRTABLE_BASE_ID    = your_base_id_here
AIRTABLE_TABLE_NAME = your_table_id_here

✅ Make sure your Time_stamp field in Airtable is set to:

Type: Date
**With time enabled`
Otherwise, logging will fail!

5. Deploy to Railway

Go to: https://railway.app
Click New Project → Deploy from GitHub Repo
Select the repo you cloned or created from template
✅ Done — the bot will:

Auto-apply to jobs from Remotive, RemoteOK, and WeWorkRemotely
Log to Airtable and CSV
Run 24/7 in the background — no coding or manual work needed

Need Help?

📩 Email support: jtxcode@yahoo.com



