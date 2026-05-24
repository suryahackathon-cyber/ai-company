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

load_dotenv()

GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITLAB_TOKEN    = os.getenv("GITLAB_TOKEN")
GITLAB_USERNAME = os.getenv("GITLAB_USERNAME")

print(f"Google key loaded: {GOOGLE_API_KEY[:10]}..." if GOOGLE_API_KEY else "ERROR: No Google key!")
print(f"GitHub user: {GITHUB_USERNAME}" if GITHUB_USERNAME else "ERROR: No GitHub username!")
print(f"GitLab user: {GITLAB_USERNAME}" if GITLAB_USERNAME else "ERROR: No GitLab username!")

client = genai.Client(api_key=GOOGLE_API_KEY)

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

def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()

@app.post("/run")
async def run_company(req: ProjectRequest):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=req.idea,
            config={"system_instruction": PLAN_INSTRUCTIONS}
        )
        text = clean_json(response.text)
        return json.loads(text)
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
                prompt = f"""
Project: {req.project_name}
Idea: {req.idea}

Write {description} for this project.
Return ONLY the raw {language} code.
No explanation. No markdown fences. Just the code itself.
Make it production-quality and complete.
"""
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                content = response.text.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.split("\n")[0] in ["javascript","sql","yaml","markdown","js","md"]:
                        content = "\n".join(content.split("\n")[1:])
                content = content.rstrip("`").strip()
                files.append({"filename": filename, "language": language, "content": content})
                print(f"Generated: {filename}")
                time.sleep(3)
            except Exception as fe:
                print(f"Error generating {filename}: {fe}")
                files.append({"filename": filename, "language": language, "content": f"// Error generating this file: {str(fe)}"})
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
Messages must be realistic, specific to this project, show disagreement and negotiation.
No generic responses. Reference actual tech stack, timeline, costs.
Return ONLY the JSON array. No markdown. No explanation.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = clean_json(response.text)
        return {"messages": json.loads(text)}
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
        print(f"Repo created: {repo_url}")
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
                    print(f"Pushed: {file['filename']}")
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
                    print(f"Pushed to GitLab: {file['filename']}")
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
                    "title":       issue["title"],
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

@app.get("/health")
def health():
    return {"status": "AI Company backend running"}

@app.get("/")
def root():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

