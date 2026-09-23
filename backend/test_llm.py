from app.core.config import settings
from app.ai.llm.factory import LLMFactory

def test_gemini():
    print("Testing LLM Provider:", settings.LLM_PROVIDER)
    try:
        provider = LLMFactory.get_provider()
        print("Provider instantiated successfully:", type(provider).__name__)
        
        # Test a simple classification if there's a quick method we can call
        # Or just checking initialization is enough to confirm connection string/key is loaded.
        
    except Exception as e:
        print("Error instantiating LLM:", str(e))

if __name__ == "__main__":
    test_gemini()
