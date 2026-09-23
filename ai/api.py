from fastapi import FastAPI
from config import ai_config

app = FastAPI(title="AI Model Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "provider": ai_config.AI_PROVIDER}
