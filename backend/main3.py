from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os, json, traceback

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

INSTRUCTIONS = """
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

@app.post("/run")
async def run_company(req: ProjectRequest):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=req.idea,
            config={"system_instruction": INSTRUCTIONS}
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}

@app.get("/")
def root():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

