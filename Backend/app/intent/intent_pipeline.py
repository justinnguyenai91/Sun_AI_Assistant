from app.adapters import llama_client, ollama_client
from app.intent.llm_intent_parser import LLMIntentParser
from app.settings import settings

# Chọn adapter phù hợp
if settings.BACKEND.lower() == "ollama":
    llm_client = ollama_client
else:
    llm_client = llama_client

# Tạo instance intent parser
intent_parser = LLMIntentParser(llm_client=llm_client, enable_llm=True)
