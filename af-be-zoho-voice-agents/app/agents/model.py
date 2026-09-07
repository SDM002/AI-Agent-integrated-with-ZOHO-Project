"""LLM Instance Enabling Multi-Agent Coordination and Execution."""
from langchain_openai import AzureChatOpenAI
from app.config import SETTINGS

model = AzureChatOpenAI(
    azure_endpoint=SETTINGS.AZURE_OPENAI_ENDPOINT,
    api_key=SETTINGS.AZURE_OPENAI_API_KEY,
    azure_deployment=SETTINGS.AZURE_OPENAI_DEPLOYMENT,
    api_version=SETTINGS.AZURE_OPENAI_API_VERSION,
    temperature=SETTINGS.AGENT_TEMPERATURE,
)
