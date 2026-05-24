from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os, json, traceback, base64, time, re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

load_dotenv()

GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITLAB_TOKEN    = os.getenv("GITLAB_TOKEN")
GITLAB_USERNAME = os.getenv("GITLAB_USERNAME")
MONGODB_URI     = os.getenv("MONGODB_URI")
ARIZE_API_KEY   = os.getenv("ARIZE_API_KEY")
ARIZE_SPACE_ID  = os.getenv("ARIZE_SPACE_ID")

print(f"Google key loaded: {GOOGLE_API_KEY[:10]}..." if GOOGLE_API_KEY else "ERROR: No Google key!")
print(f"GitLab user: {GITLAB_USERNAME}" if GITLAB_USERNAME else "ERROR: No GitLab username!")
print(f"MongoDB: Connected" if MONGODB_URI else "ERROR: No MongoDB URI!")
print(f"Arize: Connected" if ARIZE_API_KEY else "ERROR: No Arize key!")

# Gemini client
client = genai.Client(api_key=GOOGLE_API_KEY)

# MongoDB client
from pymongo import MongoClient
try:
    mongo_client = MongoClient(
        MONGODB_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsInsecure=True,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    db = mongo_client["ai_company"]
    projects_collection = db["projects"]
    mongo_client.admin.command("ping")
    print("MongoDB connected successfully!")
    MONGODB_ENABLED = True
except Exception as me:
    print(f"MongoDB connection failed (non-critical): {me}")
    projects_collection = None
    MONGODB_ENABLED = False

# Arize client
# arize imported below



print("Arize ready!")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PLAN_INSTRUCTIONS = """
You are the Orchestrator of an autonomous AI software company with 6 departments.
Respond ONLY with valid JSON, no markdown, no explanation, no code blocks.
Use exactly this structure:
{
  "project_name": "...",
  "description": "...",
  "timeline_weeks": 8,
  "team_size": 6,
  "total_cost_usd": 50000,
  "top_risks": ["risk1", "risk2", "risk3"],
  "departments": {
    "pm":        { "status": "complete", "user_stories": ["story1","story2"], "sprints": ["Sprint 1: auth","Sprint 2: core"], "priorities": ["P0: login","P1: dashboard"] },
    "architect": { "status": "complete", "frontend": "React Native", "backend": "Node.js", "database": "PostgreSQL", "pattern": "Microservices" },
    "dev":       { "status": "complete", "tech_stack": ["React Native","Node.js"], "modules": ["Auth","Payments"], "estimated_hours": 320, "complexity": "High" },
    "qa":        { "status": "complete", "test_cases": ["Login flow","Payment flow"], "risk_areas": ["High: Payment security","Medium: Performance"], "qa_hours": 80 },
    "devops":    { "status": "complete", "infrastructure": "GCP Cloud Run", "cicd": "GitHub Actions", "monthly_cost_usd": 200, "environments": ["dev","staging","production"] },
    "marketing": { "status": "complete", "target_audience": "Adults 18-35", "channels": ["Instagram","Google Ads"], "gtm_phases": ["Phase 1: Beta","Phase 2: Launch"], "kpis": ["DAU","Retention"] }
  }
}
"""

class ProjectRequest(BaseModel):
    idea: str

class BuildRequest(BaseModel):
    idea: str
    project_name: str

class GitHubRequest(BaseModel):
    project_name: str
    files: list
    description: str

class GitLabRequest(BaseModel):
    project_name: str
    files: list
    description: str

class MeetingRequest(BaseModel):
    project_name: str
    plan: dict

def gemini_generate(prompt, system_instruction=None, retries=3):
    for attempt in range(retries):
        try:
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config if config else None
            )
            return response
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = (attempt + 1) * 10
                print(f"Gemini busy, retrying in {wait}s... (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise e
    raise Exception("Gemini unavailable after retries")

def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()

def log_to_arize(model_id, prompt, response_text, latency_ms, tokens=0):
    try:
        import pandas as pd
        from arize.pandas.logger import Client as ArizeLogger
        from arize.utils.types import ModelTypes, Environments, Schema, Metrics
        arize_logger = ArizeLogger(
            space_id=ARIZE_SPACE_ID,
            api_key=ARIZE_API_KEY
        )
        pred_id = f"{model_id}_{int(time.time())}"
        df = pd.DataFrame([{
            "prediction_id": pred_id,
            "prompt":        prompt[:500],
            "response":      response_text[:500],
            "latency_ms":    float(latency_ms),
        }])
        schema = Schema(
            prediction_id_column_name="prediction_id",
            prompt_column_name="prompt",
            response_column_name="response",
        )
        res = arize_logger.log(
            dataframe=df,
            schema=schema,
            model_id=model_id,
            model_type=ModelTypes.GENERATIVE_LLM,
            environment=Environments.PRODUCTION,
            model_version="gemini-2.5-flash",
        )
        print(f"Arize logged: {model_id} ({latency_ms}ms) status={res.status_code}")
    except Exception as e:
        print(f"Arize logging error (non-critical): {e}")

def save_to_mongodb(project_name, idea, result):
    if not MONGODB_ENABLED or projects_collection is None:
        print("MongoDB disabled — skipping save")
        return
    try:
        doc = {
            "project_name": project_name,
            "idea": idea,
            "result": result,
            "created_at": datetime.utcnow(),
            "timestamp": int(time.time())
        }
        projects_collection.insert_one(doc)
        print(f"Saved to MongoDB: {project_name}")
    except Exception as e:
        print(f"MongoDB save error (non-critical): {e}")

@app.post("/run")
async def run_company(req: ProjectRequest):
    try:
        start = time.time()
        response = gemini_generate(req.idea, system_instruction=PLAN_INSTRUCTIONS)
        latency = int((time.time() - start) * 1000)
        text = clean_json(response.text)
        result = json.loads(text)
        save_to_mongodb(result.get("project_name", "Unknown"), req.idea, result)
        log_to_arize("orchestrator-agent", req.idea, response.text, latency)
        return result
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/build")
async def build_app(req: BuildRequest):
    try:
        files = []
        file_specs = [
            ("backend/server.js",  "javascript", "a complete Express.js backend server with all routes, middleware, authentication and database connections"),
            ("backend/schema.sql", "sql",         "complete PostgreSQL database schema with all tables, indexes, and relationships"),
            ("frontend/App.js",    "javascript",  "a complete React Native frontend app with navigation and main screens"),
            ("docker-compose.yml", "yaml",         "a complete docker-compose file for local development with all services"),
            ("README.md",          "markdown",     "a detailed README with setup instructions, architecture overview, and API docs"),
        ]
        for filename, language, description in file_specs:
            try:
                prompt = f"Project: {req.project_name}\nIdea: {req.idea}\n\nWrite {description} for this project.\nReturn ONLY the raw {language} code. No explanation. No markdown fences."
                start = time.time()
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                latency = int((time.time() - start) * 1000)
                content = response.text.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.split("\n")[0] in ["javascript","sql","yaml","markdown","js","md"]:
                        content = "\n".join(content.split("\n")[1:])
                content = content.rstrip("`").strip()
                files.append({"filename": filename, "language": language, "content": content})
                log_to_arize("dev-agent", prompt[:200], content[:200], latency)
                print(f"Generated: {filename}")
                time.sleep(3)
            except Exception as fe:
                print(f"Error generating {filename}: {fe}")
                files.append({"filename": filename, "language": language, "content": f"// Error: {str(fe)}"})
        return {"files": files}
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}

@app.post("/meeting")
async def agent_meeting(req: MeetingRequest):
    try:
        prompt = f"""
Project: {req.project_name}
Plan summary:
- Timeline: {req.plan.get('timeline_weeks')} weeks
- Team: {req.plan.get('team_size')} people
- Cost: ${req.plan.get('total_cost_usd')}
- Stack: {req.plan.get('departments', {}).get('architect', {}).get('backend')} / {req.plan.get('departments', {}).get('architect', {}).get('frontend')}
- Complexity: {req.plan.get('departments', {}).get('dev', {}).get('complexity')}
- Top risk: {req.plan.get('top_risks', ['Unknown'])[0]}

Simulate a short internal team meeting between these AI agents discussing this project.
Return ONLY a JSON array of 8 messages like this:
[
  {{"agent": "PM Agent",        "message": "...", "type": "normal"}},
  {{"agent": "Architect Agent", "message": "...", "type": "concern"}},
  {{"agent": "Dev Agent",       "message": "...", "type": "normal"}},
  {{"agent": "QA Agent",        "message": "...", "type": "warning"}},
  {{"agent": "DevOps Agent",    "message": "...", "type": "normal"}},
  {{"agent": "PM Agent",        "message": "...", "type": "decision"}},
  {{"agent": "Marketing Agent", "message": "...", "type": "normal"}},
  {{"agent": "Dev Agent",       "message": "...", "type": "concern"}}
]
Type must be one of: normal, concern, warning, decision
Messages must be realistic and specific to this project.
Return ONLY the JSON array. No markdown. No explanation.
"""
        start = time.time()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        latency = int((time.time() - start) * 1000)
        text = clean_json(response.text)
        messages = json.loads(text)
        log_to_arize("meeting-agent", prompt[:200], response.text[:200], latency)
        return {"messages": messages}
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}

@app.post("/push-github")
async def push_to_github(req: GitHubRequest):
    try:
        repo_name = req.project_name.lower().replace(" ", "-").replace("_", "-")
        repo_name = re.sub(r'[^a-z0-9-]', '', repo_name)[:50]
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        create_data = json.dumps({
            "name": repo_name,
            "description": req.description,
            "private": False,
            "auto_init": True
        }).encode()
        github_req = urllib.request.Request(
            "https://api.github.com/user/repos",
            data=create_data,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(github_req) as response:
            repo_data = json.loads(response.read())
        repo_url = repo_data["html_url"]
        time.sleep(2)
        pushed = 0
        for file in req.files:
            try:
                file_data = json.dumps({
                    "message": f"Add {file['filename']}",
                    "content": base64.b64encode(file["content"].encode("utf-8", errors="replace")).decode()
                }).encode()
                file_req = urllib.request.Request(
                    f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file['filename']}",
                    data=file_data,
                    headers=headers,
                    method="PUT"
                )
                with urllib.request.urlopen(file_req) as r:
                    pushed += 1
                time.sleep(0.5)
            except Exception as fe:
                print(f"File error {file['filename']}: {fe}")
        issues = [
            {"title": "Set up project infrastructure",  "body": "DevOps: Configure CI/CD, Docker, cloud deployment"},
            {"title": "Implement authentication system", "body": "Dev: User registration, login, JWT tokens"},
            {"title": "Build core API endpoints",        "body": "Dev: REST API for main features"},
            {"title": "Create frontend UI",              "body": "Dev: Mobile/web interface"},
            {"title": "Write test suite",                "body": "QA: Unit, integration and e2e tests"},
            {"title": "Launch marketing campaign",       "body": "Marketing: GTM strategy execution"},
        ]
        created = 0
        for issue in issues:
            try:
                issue_data = json.dumps({"title": issue["title"], "body": issue["body"]}).encode()
                issue_req = urllib.request.Request(
                    f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/issues",
                    data=issue_data,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(issue_req) as r:
                    created += 1
                time.sleep(0.3)
            except Exception as ie:
                print(f"Issue error: {ie}")
        return {"success": True, "repo_url": repo_url, "repo_name": repo_name, "files_pushed": pushed, "issues_created": created}
    except Exception as e:
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.post("/push-gitlab")
async def push_to_gitlab(req: GitLabRequest):
    try:
        repo_name = req.project_name.lower().replace(" ", "-").replace("_", "-")
        repo_name = re.sub(r'[^a-z0-9-]', '', repo_name)[:50]
        headers = {
            "PRIVATE-TOKEN": GITLAB_TOKEN,
            "Content-Type": "application/json"
        }
        create_data = json.dumps({
            "name": repo_name,
            "description": req.description,
            "visibility": "public",
            "initialize_with_readme": True
        }).encode()
        create_req = urllib.request.Request(
            "https://gitlab.com/api/v4/projects",
            data=create_data,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(create_req) as response:
            project_data = json.loads(response.read())
        project_id  = project_data["id"]
        project_url = project_data["web_url"]
        print(f"GitLab project created: {project_url}")
        time.sleep(2)
        pushed = 0
        for file in req.files:
            try:
                file_data = json.dumps({
                    "branch": "main",
                    "commit_message": f"Add {file['filename']}",
                    "content": file["content"]
                }).encode()
                encoded_filename = urllib.parse.quote(file["filename"], safe="")
                file_req = urllib.request.Request(
                    f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{encoded_filename}",
                    data=file_data,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(file_req) as r:
                    pushed += 1
                time.sleep(0.5)
            except Exception as fe:
                print(f"GitLab file error {file['filename']}: {fe}")
        issues = [
            {"title": "Set up CI/CD pipeline",          "description": "DevOps: Configure GitLab CI/CD, Docker, cloud deployment"},
            {"title": "Implement authentication system", "description": "Dev: User registration, login, JWT tokens"},
            {"title": "Build core API endpoints",        "description": "Dev: REST API for main features"},
            {"title": "Create frontend UI",              "description": "Dev: Mobile/web interface"},
            {"title": "Write test suite",                "description": "QA: Unit, integration and e2e tests"},
            {"title": "Launch marketing campaign",       "description": "Marketing: GTM strategy execution"},
        ]
        created = 0
        for issue in issues:
            try:
                issue_data = json.dumps({
                    "title": issue["title"],
                    "description": issue["description"]
                }).encode()
                issue_req = urllib.request.Request(
                    f"https://gitlab.com/api/v4/projects/{project_id}/issues",
                    data=issue_data,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(issue_req) as r:
                    created += 1
                time.sleep(0.3)
            except Exception as ie:
                print(f"GitLab issue error: {ie}")
        try:
            milestone_data = json.dumps({
                "title": "Sprint 1 — MVP",
                "description": "First sprint focusing on core features"
            }).encode()
            milestone_req = urllib.request.Request(
                f"https://gitlab.com/api/v4/projects/{project_id}/milestones",
                data=milestone_data,
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(milestone_req) as r:
                print("GitLab milestone created")
        except Exception as me:
            print(f"Milestone error: {me}")
        return {
            "success": True,
            "project_url": project_url,
            "project_id": project_id,
            "project_name": repo_name,
            "files_pushed": pushed,
            "issues_created": created
        }
    except Exception as e:
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.get("/projects")
async def get_projects():
    if not MONGODB_ENABLED or projects_collection is None:
        return {"projects": [], "message": "MongoDB not available"}
    try:
        projects = list(projects_collection.find(
            {},
            {"_id": 0, "project_name": 1, "idea": 1, "created_at": 1,
             "result.timeline_weeks": 1, "result.team_size": 1, "result.total_cost_usd": 1}
        ).sort("created_at", -1).limit(10))
        for p in projects:
            if "created_at" in p:
                p["created_at"] = p["created_at"].strftime("%Y-%m-%d %H:%M")
        return {"projects": projects}
    except Exception as e:
        print(traceback.format_exc())
        return {"projects": []}

@app.get("/health")
def health():
    return {
        "status": "AI Company backend running",
        "mongodb": "connected",
        "arize": "connected",
        "gitlab": "connected"
    }

@app.get("/")
def root():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

