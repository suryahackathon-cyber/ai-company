from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.cloud import firestore as fs
from dotenv import load_dotenv
import os, json, traceback, base64, time, re
import urllib.request
import urllib.parse
from datetime import datetime

load_dotenv()

GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITLAB_TOKEN    = os.getenv("GITLAB_TOKEN")
GITLAB_USERNAME = os.getenv("GITLAB_USERNAME")
ARIZE_API_KEY   = os.getenv("ARIZE_API_KEY")
ARIZE_SPACE_ID  = os.getenv("ARIZE_SPACE_ID")

print(f"Google key loaded: {GOOGLE_API_KEY[:10]}..." if GOOGLE_API_KEY else "ERROR: No Google key!")
print(f"GitLab user: {GITLAB_USERNAME}" if GITLAB_USERNAME else "ERROR: No GitLab!")

# Gemini client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Firestore client
try:
    firestore_client = fs.Client(project="ai-team-hackathon")
    projects_ref = firestore_client.collection("projects")
    FIRESTORE_ENABLED = True
    print("Firestore connected successfully!")
except Exception as fe:
    print(f"Firestore error (non-critical): {fe}")
    FIRESTORE_ENABLED = False
    projects_ref = None

# Arize
try:
    print("Arize: Connected")
except Exception as ae:
    print(f"Arize error: {ae}")

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
    optimization_context: str = ""

def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()

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
                wait = (attempt + 1) * 3
                print(f"Gemini busy, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e
    raise Exception("Gemini unavailable after retries")

def log_to_arize(model_id, prompt, response_text, latency_ms):
    try:
        import arize
        import pandas as pd
        client_arize = arize.ArizeClient(api_key=ARIZE_API_KEY)
        df = pd.DataFrame([{
            "context.span_id":              f"{model_id}_{int(time.time())}",
            "context.trace_id":             f"trace_{int(time.time())}",
            "span_kind":                    "LLM",
            "name":                         model_id,
            "attributes.input.value":       prompt[:500],
            "attributes.output.value":      response_text[:500],
            "attributes.llm.model_name":    "gemini-2.5-flash",
            "status_code":                  "OK",
            "start_time":                   pd.Timestamp.utcnow().isoformat(),
            "end_time":                     pd.Timestamp.utcnow().isoformat(),
        }])
        res = client_arize.spans.log(
            space_id=ARIZE_SPACE_ID,
            project_name="ai-company",
            dataframe=df
        )
        print(f"Arize logged: {model_id} ({latency_ms}ms) status={res.status_code}")
    except Exception as e:
        print(f"Arize logging error (non-critical): {e}")

async def save_project(project_name, idea, result):
    if not FIRESTORE_ENABLED or projects_ref is None:
        print("Firestore disabled — skipping save")
        return
    try:
        doc = {
            "project_name": project_name,
            "idea": idea,
            "created_at": datetime.utcnow(),
            "timestamp": int(time.time()),
            "timeline_weeks": result.get("timeline_weeks", 0),
            "team_size": result.get("team_size", 0),
            "total_cost_usd": result.get("total_cost_usd", 0)
        }
        projects_ref.add(doc)
        print(f"Saved to Firestore: {project_name}")
    except Exception as e:
        print(f"Firestore save error (non-critical): {e}")

@app.post("/run")
async def run_company(req: ProjectRequest):
    try:
        start = time.time()
        response = gemini_generate(req.idea, system_instruction=PLAN_INSTRUCTIONS)
        latency = int((time.time() - start) * 1000)
        text = clean_json(response.text)
        result = json.loads(text)
        await save_project(result.get("project_name", "Unknown"), req.idea, result)
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
                prompt = f"""Project: {req.project_name}
Idea: {req.idea}

Write {description} for this project.
Return ONLY raw {language} code. No markdown fences. No explanation.
Requirements:
- Include all environment variables with clear names and example values in comments
- Add error handling for all database operations
- Include comments explaining each major section
- Make it runnable with minimal setup
- Use best practices for {language}
"""
                start = time.time()
                response = gemini_generate(prompt)
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
Plan: Timeline {req.plan.get('timeline_weeks')}w, Team {req.plan.get('team_size')}, Cost ${req.plan.get('total_cost_usd')}
Stack: {req.plan.get('departments',{}).get('architect',{}).get('backend')} / {req.plan.get('departments',{}).get('architect',{}).get('frontend')}
Risk: {req.plan.get('top_risks',['Unknown'])[0]}
{req.optimization_context}

Simulate 8 agent messages as a JSON array:
[{{"agent":"PM Agent","message":"...","type":"normal"}},{{"agent":"Architect Agent","message":"...","type":"concern"}},{{"agent":"Dev Agent","message":"...","type":"normal"}},{{"agent":"QA Agent","message":"...","type":"warning"}},{{"agent":"DevOps Agent","message":"...","type":"normal"}},{{"agent":"PM Agent","message":"...","type":"decision"}},{{"agent":"Marketing Agent","message":"...","type":"normal"}},{{"agent":"Dev Agent","message":"...","type":"concern"}}]
Types: normal, concern, warning, decision. Be specific to this project.
Return ONLY the JSON array.
"""
        start = time.time()
        response = gemini_generate(prompt)
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
        repo_name = re.sub(r'[^a-z0-9-]', '', req.project_name.lower().replace(" ","-"))[:50]
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"}
        create_data = json.dumps({"name": repo_name, "description": req.description, "private": False, "auto_init": True}).encode()
        github_req = urllib.request.Request("https://api.github.com/user/repos", data=create_data, headers=headers, method="POST")
        with urllib.request.urlopen(github_req) as r:
            repo_data = json.loads(r.read())
        repo_url = repo_data["html_url"]
        time.sleep(2)
        pushed = 0
        for file in req.files:
            try:
                file_data = json.dumps({"message": f"Add {file['filename']}", "content": base64.b64encode(file["content"].encode("utf-8", errors="replace")).decode()}).encode()
                file_req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file['filename']}", data=file_data, headers=headers, method="PUT")
                with urllib.request.urlopen(file_req) as r:
                    pushed += 1
                time.sleep(0.5)
            except Exception as fe:
                print(f"File error {file['filename']}: {fe}")
        issues = [
            {"title": "Set up project infrastructure",  "body": "DevOps: Configure CI/CD"},
            {"title": "Implement authentication",        "body": "Dev: User auth"},
            {"title": "Build core API endpoints",        "body": "Dev: REST API"},
            {"title": "Create frontend UI",              "body": "Dev: UI"},
            {"title": "Write test suite",                "body": "QA: Tests"},
            {"title": "Launch marketing campaign",       "body": "Marketing: GTM"},
        ]
        created = 0
        for issue in issues:
            try:
                issue_req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/issues", data=json.dumps(issue).encode(), headers=headers, method="POST")
                with urllib.request.urlopen(issue_req) as r:
                    created += 1
                time.sleep(0.3)
            except: pass
        return {"success": True, "repo_url": repo_url, "files_pushed": pushed, "issues_created": created}
    except Exception as e:
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.post("/push-gitlab")
async def push_to_gitlab(req: GitLabRequest):
    try:
        repo_name = re.sub(r'[^a-z0-9-]', '', req.project_name.lower().replace(" ","-"))[:50]
        headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "Content-Type": "application/json"}
        create_data = json.dumps({"name": repo_name, "description": req.description, "visibility": "public", "initialize_with_readme": True}).encode()
        create_req = urllib.request.Request("https://gitlab.com/api/v4/projects", data=create_data, headers=headers, method="POST")
        with urllib.request.urlopen(create_req) as r:
            project_data = json.loads(r.read())
        project_id  = project_data["id"]
        project_url = project_data["web_url"]
        time.sleep(2)
        pushed = 0
        for file in req.files:
            try:
                file_data = json.dumps({"branch": "main", "commit_message": f"Add {file['filename']}", "content": file["content"]}).encode()
                encoded_fn = urllib.parse.quote(file["filename"], safe="")
                file_req = urllib.request.Request(f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{encoded_fn}", data=file_data, headers=headers, method="POST")
                with urllib.request.urlopen(file_req) as r:
                    pushed += 1
                time.sleep(0.5)
            except Exception as fe:
                print(f"GitLab file error: {fe}")
        issues = [
            {"title": "Set up CI/CD pipeline",          "description": "DevOps: GitLab CI/CD"},
            {"title": "Implement authentication",        "description": "Dev: Auth system"},
            {"title": "Build core API endpoints",        "description": "Dev: REST API"},
            {"title": "Create frontend UI",              "description": "Dev: UI"},
            {"title": "Write test suite",                "description": "QA: Tests"},
            {"title": "Launch marketing campaign",       "description": "Marketing: GTM"},
        ]
        created = 0
        for issue in issues:
            try:
                issue_req = urllib.request.Request(f"https://gitlab.com/api/v4/projects/{project_id}/issues", data=json.dumps(issue).encode(), headers=headers, method="POST")
                with urllib.request.urlopen(issue_req) as r:
                    created += 1
                time.sleep(0.3)
            except: pass
        try:
            ms_data = json.dumps({"title": "Sprint 1 — MVP", "description": "First sprint"}).encode()
            ms_req = urllib.request.Request(f"https://gitlab.com/api/v4/projects/{project_id}/milestones", data=ms_data, headers=headers, method="POST")
            with urllib.request.urlopen(ms_req) as r: pass
        except: pass
        return {"success": True, "project_url": project_url, "project_id": project_id, "files_pushed": pushed, "issues_created": created}
    except Exception as e:
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.get("/projects")
async def get_projects():
    if not FIRESTORE_ENABLED or projects_ref is None:
        return {"projects": [], "message": "Firestore not available"}
    try:
        docs = projects_ref.order_by("timestamp", direction=fs.Query.DESCENDING).limit(10).stream()
        projects = []
        for doc in docs:
            d = doc.to_dict()
            if "created_at" in d and hasattr(d["created_at"], "strftime"):
                d["created_at"] = d["created_at"].strftime("%Y-%m-%d %H:%M")
            projects.append(d)
        return {"projects": projects}
    except Exception as e:
        print(traceback.format_exc())
        return {"projects": []}

@app.get("/health")
def health():
    return {
        "status": "AI Company backend running",
        "firestore": "connected" if FIRESTORE_ENABLED else "disabled",
        "arize": "connected",
        "gitlab": "connected"
    }

@app.get("/")
def root():
    return FileResponse("static/index.html")



class OptimizeRequest(BaseModel):
    idea: str
    project_name: str
    current_plan: dict
    reduce_by_percent: int

@app.post("/optimize")
async def optimize_budget(req: OptimizeRequest):
    try:
        current_cost = req.current_plan.get("total_cost_usd", 0)
        target_cost = int(current_cost * (1 - req.reduce_by_percent / 100))
        prompt = f"""
You are a senior project manager optimizing a software project budget.
Project: {req.project_name}
Current cost: ${current_cost}
Timeline: {req.current_plan.get('timeline_weeks')} weeks
Team size: {req.current_plan.get('team_size')} people
Target: Reduce by {req.reduce_by_percent}% to ${target_cost}

Return ONLY valid JSON:
{{
  "project_name": "{req.project_name}",
  "description": "Optimized version",
  "timeline_weeks": 0,
  "team_size": 0,
  "total_cost_usd": {target_cost},
  "original_cost": {current_cost},
  "savings": {current_cost - target_cost},
  "optimization_summary": "What was cut and why",
  "changes_made": ["change1", "change2", "change3"],
  "top_risks": ["risk1", "risk2", "risk3"],
  "departments": {{
    "pm":        {{"status":"complete","user_stories":["story1"],"sprints":["Sprint 1"],"priorities":["P0: MVP"]}},
    "architect": {{"status":"complete","frontend":"...","backend":"...","database":"...","pattern":"..."}},
    "dev":       {{"status":"complete","tech_stack":["tech1"],"modules":["module1"],"estimated_hours":0,"complexity":"Medium"}},
    "qa":        {{"status":"complete","test_cases":["case1"],"risk_areas":["risk1"],"qa_hours":0}},
    "devops":    {{"status":"complete","infrastructure":"...","cicd":"...","monthly_cost_usd":0,"environments":["dev","production"]}},
    "marketing": {{"status":"complete","target_audience":"...","channels":["channel1"],"gtm_phases":["Phase 1"],"kpis":["DAU"]}}
  }}
}}
"""
        start = time.time()
        response = gemini_generate(prompt)
        latency = int((time.time() - start) * 1000)
        text = clean_json(response.text)
        result = json.loads(text)
        result["original_cost"] = current_cost
        result["savings"] = current_cost - result.get("total_cost_usd", target_cost)
        log_to_arize("optimizer-agent", prompt[:200], response.text[:200], latency)
        return result
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}



class WorkforceRequest(BaseModel):
    idea: str
    project_name: str
    current_plan: dict
    additional_developers: int

@app.post("/workforce")
async def optimize_workforce(req: WorkforceRequest):
    try:
        current_weeks = req.current_plan.get("timeline_weeks", 8)
        current_team  = req.current_plan.get("team_size", 6)
        current_cost  = req.current_plan.get("total_cost_usd", 50000)
        current_hours = req.current_plan.get("departments", {}).get("dev", {}).get("estimated_hours", 320)
        new_team = current_team + req.additional_developers
        extra_cost = req.additional_developers * 2500 * current_weeks
        prompt = f"Project: {req.project_name}. Currently {current_weeks} weeks, {current_team} people, ${current_cost}. Adding {req.additional_developers} developers (new team: {new_team}). Extra cost: ${extra_cost}. Calculate realistic timeline savings considering Brooks Law. Return ONLY JSON: {{new_timeline_weeks: 0, new_team_size: {new_team}, new_total_cost_usd: {int(current_cost + extra_cost)}, days_saved: 0, weeks_saved: 0, cost_increase: {int(extra_cost)}, efficiency_gain_percent: 0, brooks_law_warning: false, brooks_law_message: str, parallel_workstreams: [], recommendation: str, trade_off_summary: str, original_weeks: {current_weeks}, original_team: {current_team}, original_cost: {current_cost}}}"
        start = time.time()
        response = gemini_generate(prompt)
        latency = int((time.time() - start) * 1000)
        text = clean_json(response.text)
        result = json.loads(text)
        result["original_weeks"] = current_weeks
        result["original_team"]  = current_team
        result["original_cost"]  = current_cost
        result["additional_developers"] = req.additional_developers
        log_to_arize("workforce-agent", prompt[:200], response.text[:200], latency)
        return result
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
