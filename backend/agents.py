from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

# PM Agent
pm_agent_google_search_agent = LlmAgent(
  name='PM_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)
pm_agent_url_context_agent = LlmAgent(
  name='PM_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)
pm_agent = LlmAgent(
  name='pm_agent_2',
  model='gemini-2.5-flash',
  description='You are a Product Manager AI. Given a software project, produce',
  sub_agents=[],
  instruction='- User stories (as a user I want...)\n- Feature list with priorities (P0/P1/P2)\n- Sprint breakdown (Sprint 1, Sprint 2...)\n- Acceptance criteria per feature\nReturn structured JSON.',
  tools=[
    agent_tool.AgentTool(agent=pm_agent_google_search_agent),
    agent_tool.AgentTool(agent=pm_agent_url_context_agent)
  ],
)

# Architect Agent
architect_agent_search = LlmAgent(
  name='Architect_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)
architect_agent_url = LlmAgent(
  name='Architect_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)
architect_agent = LlmAgent(
  name='architect_agent',
  model='gemini-2.5-flash',
  description='You are a Software Architect AI',
  sub_agents=[],
  instruction='Design the full technical architecture:\n- Frontend stack\n- Backend services\n- Database schema\n- Infrastructure requirements\nReturn structured JSON.',
  tools=[
    agent_tool.AgentTool(agent=architect_agent_search),
    agent_tool.AgentTool(agent=architect_agent_url)
  ],
)

# Dev Agent
dev_agent_search = LlmAgent(
  name='Dev_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)
dev_agent_url = LlmAgent(
  name='Dev_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)
dev_agent = LlmAgent(
  name='dev_agent',
  model='gemini-2.5-flash',
  description='You are a Senior Software Developer AI in an autonomous software company',
  sub_agents=[],
  instruction='Given a project request, produce:\n- Tech stack recommendation\n- Module breakdown\n- Estimated hours\n- Complexity rating\n- API endpoints\nReturn structured JSON only.',
  tools=[
    agent_tool.AgentTool(agent=dev_agent_search),
    agent_tool.AgentTool(agent=dev_agent_url)
  ],
)

# QA Agent
qa_agent_search = LlmAgent(
  name='QA_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)
qa_agent_url = LlmAgent(
  name='QA_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)
qa_agent = LlmAgent(
  name='qa_agent',
  model='gemini-2.5-flash',
  description='You are a Senior QA Engineer AI.',
  sub_agents=[],
  instruction='Given a project request, produce:\n- Test strategy\n- Test cases per feature\n- Security checklist\n- Bug risk areas\n- Estimated QA hours\nReturn structured JSON only.',
  tools=[
    agent_tool.AgentTool(agent=qa_agent_search),
    agent_tool.AgentTool(agent=qa_agent_url)
  ],
)

# DevOps Agent
devops_agent_search = LlmAgent(
  name='DevOps_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)
devops_agent_url = LlmAgent(
  name='DevOps_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)
devops_agent = LlmAgent(
  name='devops_agent',
  model='gemini-2.5-flash',
  description='You are a Senior DevOps Engineer AI.',
  sub_agents=[],
  instruction='Given a project request, produce:\n- Cloud infrastructure plan\n- CI/CD pipeline\n- Cost estimate\n- Scaling strategy\nReturn structured JSON only.',
  tools=[
    agent_tool.AgentTool(agent=devops_agent_search),
    agent_tool.AgentTool(agent=devops_agent_url)
  ],
)

# Marketing Agent
marketing_agent_search = LlmAgent(
  name='Marketing_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)
marketing_agent_url = LlmAgent(
  name='Marketing_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)
marketing_agent = LlmAgent(
  name='marketing_agent',
  model='gemini-2.5-flash',
  description='You are a Senior Marketing Strategist AI.',
  sub_agents=[],
  instruction='Given a project request, produce:\n- Target audience\n- Value proposition\n- GTM strategy\n- Marketing channels\n- KPIs\nReturn structured JSON only.',
  tools=[
    agent_tool.AgentTool(agent=marketing_agent_search),
    agent_tool.AgentTool(agent=marketing_agent_url)
  ],
)

# Root Orchestrator Agent
root_agent = LlmAgent(
  name='My_Agent',
  model='gemini-2.5-flash',
  description='Orchestrator of an autonomous AI software company.',
  sub_agents=[pm_agent, architect_agent, dev_agent, qa_agent, devops_agent, marketing_agent],
  instruction='You are the orchestrator of an autonomous AI software company.\nWhen given a project request:\n1. Delegate to PM, Architect, Developer, QA, DevOps, Marketing agents\n2. Return a structured JSON plan with all department outputs\nReturn JSON format only.',
  tools=[],
)
