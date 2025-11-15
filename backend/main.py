from fastapi import FastAPI
from rag import RAGPipeline
from model import SLMModel
import os

app = FastAPI()

rag = RAGPipeline()
if not os.path.exists("./chroma_db"):
    rag.load_docs()


slm = SLMModel()

@app.get("/ask")
def ask(q: str):
    # Step 1: Get context from RAG
    context = rag.query(q)

    # Step 2: Generate DSS output first
    dss_prompt = f"Context:\n{context}\n\nUser Query: {q}\n\nAnswer in simple terms:"
    dss_output = slm.generate(dss_prompt)

    # Step 3: Verification prompt for SLM
    verification_prompt = f"""
    You are an AI verification agent.

    1. User Query: {q}
    2. DSS Output: {dss_output}
    3. Context Documents (from RAG): {context}

    Tasks:
    - Check compliance with requirements in the context
    - Check safety and ethical constraints
    - Determine if any rules are violated

    Return JSON:
    {{
      "pass_fail": "PASS or FAIL",
      "risk_score": 0.0-1.0,
      "violated_requirements": [...],
      "explanation": "Short explanation why it passed or failed"
    }}
    """

    verification_result = slm.generate(verification_prompt)

    # Optional: parse verification_result as JSON if needed
    return {
        "query": q,
        "dss_output": dss_output,
        "context_used": context,
        "verification": verification_result
    }

@app.get("/")
def home():
    return {"message": "Welcome! Use /ask?q=your_question"}
