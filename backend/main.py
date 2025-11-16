from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from rag import RAGPipeline
from model import SLMModel
import os
import shutil
from typing import Dict, List
from pydantic import BaseModel

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()
if not os.path.exists("./chroma_db"):
    rag.load_docs()

slm = SLMModel()

# Create uploads directory
UPLOAD_DIR = "./data/docs/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store conversation history per session
conversations: Dict[str, List[Dict]] = {}
# Store uploaded files per session
session_files: Dict[str, List[str]] = {}

class ChatRequest(BaseModel):
    question: str
    session_id: str
    verify: bool = False

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = "default"):
    """
    Upload a file and add it to the RAG system
    session_id: to track which user uploaded which files
    """
    try:
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Track uploaded file for this session
        if session_id not in session_files:
            session_files[session_id] = []
        session_files[session_id].append(file.filename)
        
        # Load and process the file
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        ext = os.path.splitext(file.filename)[1].lower()
        
        docs = []
        if ext == '.txt':
            from langchain_community.document_loaders import TextLoader
            docs = TextLoader(file_path).load()
        elif ext == '.pdf':
            from langchain_community.document_loaders import PDFPlumberLoader
            docs = PDFPlumberLoader(file_path).load()
        elif ext == '.py':
            docs = rag.load_python_file(file_path)
        elif ext == '.ipynb':
            docs = rag.load_ipynb_file(file_path)
        elif ext == '.json':
            docs = rag.load_json_file(file_path)
        elif ext == '.csv':
            docs = rag.load_csv_file(file_path)
        elif ext in ['.md']:
            docs = rag.load_markdown_file(file_path)
        elif ext in ['.yaml', '.yml']:
            docs = rag.load_yaml_file(file_path)
        elif ext in ['.pt', '.pth']:
            docs = rag.load_pytorch_model_info(file_path)
        elif ext in ['.pkl', '.pickle']:
            docs = rag.load_pickle_file(file_path)
        elif ext in ['.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', 
                     '.rs', '.go', '.rb', '.php', '.html', '.css', '.xml', '.sh', '.r', '.sql']:
            lang_map = {
                '.js': 'javascript', '.jsx': 'javascript', '.ts': 'typescript', 
                '.tsx': 'typescript', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
                '.h': 'c', '.rs': 'rust', '.go': 'go', '.rb': 'ruby', '.php': 'php',
                '.html': 'html', '.css': 'css', '.xml': 'xml', '.sh': 'shell',
                '.r': 'r', '.sql': 'sql'
            }
            docs = rag.load_code_file(file_path, lang_map.get(ext, 'code'))
        else:
            return {
                "success": False,
                "message": f"Unsupported file type: {ext}",
                "filename": file.filename
            }
        
        # Split and add to vector store
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80
        )
        chunks = splitter.split_documents(docs)
        rag.db.add_documents(chunks)
        rag.db.persist()
        
        print(f"✓ File uploaded: {file.filename} ({len(chunks)} chunks)")
        
        return {
            "success": True,
            "message": f"File uploaded and processed successfully",
            "filename": file.filename,
            "chunks_created": len(chunks)
        }
    
    except Exception as e:
        print(f"✗ Upload error: {str(e)}")
        return {
            "success": False,
            "message": f"Error processing file: {str(e)}",
            "filename": file.filename
        }

@app.post("/ask")
def ask(request: ChatRequest):
    """
    Ask a question with conversation history (POST)
    """
    import time
    import json
    import re
    
    start_time = time.time()
    session_id = request.session_id
    question = request.question
    
    # Initialize conversation history for new sessions
    if session_id not in conversations:
        conversations[session_id] = []
    
    # Get relevant context from RAG
    context = rag.query(question, k=5)
    print(f"✓ RAG query completed in {time.time() - start_time:.2f}s")
    
    # Build conversation history
    conversation_context = ""
    if conversations[session_id]:
        conversation_context = "\n\nPrevious conversation:\n"
        # Only include last 3 exchanges to keep prompt short
        for msg in conversations[session_id][-6:]:  # 3 Q&A pairs
            conversation_context += f"{msg['role']}: {msg['content']}\n"
    
    # Add uploaded files context
    files_context = ""
    if session_id in session_files and session_files[session_id]:
        files_context = f"\n\nRecently uploaded files in this session: {', '.join(session_files[session_id])}"
    
    # Enhanced prompt with conversation history
    dss_prompt = f"""You are a helpful AI assistant analyzing documents and code.

{files_context}

Context from relevant documents:
{context}
{conversation_context}

Current User Question: {question}

Instructions:
- Use the conversation history to understand context and pronouns (like "this file", "it", "that")
- Answer based on the provided context and conversation history
- If the question refers to a recently uploaded file, use the files list above
- Be specific and reference file names when relevant
- If you cannot answer from the context, say so clearly

Answer:"""
    
    print(f"⏳ Generating response... (this may take 10-20 seconds)")
    gen_start = time.time()
    
    # Generate response with shorter output for speed
    dss_output = slm.generate(dss_prompt, max_tokens=200)
    
    # Extract just the answer (remove the prompt echo)
    answer_marker = "Answer:"
    if answer_marker in dss_output:
        dss_output = dss_output.split(answer_marker)[-1].strip()
    
    print(f"✓ Response generated in {time.time() - gen_start:.2f}s")
    
    # Store conversation history
    conversations[session_id].append({
        "role": "user",
        "content": question
    })
    conversations[session_id].append({
        "role": "assistant",
        "content": dss_output
    })
    
    # Optional verification
    verification_result = None
    if request.verify:
        print(f"⏳ Running verification...")
        verification_prompt = f"""
        Verify this response for compliance and safety.
        
        Question: {question}
        Answer: {dss_output}
        
        Return JSON only:
        {{
          "pass_fail": "PASS or FAIL",
          "risk_score": 0.0-1.0,
          "violated_requirements": [],
          "explanation": "Brief explanation"
        }}
        """
        
        ver_start = time.time()
        verification_output = slm.generate(verification_prompt, max_tokens=100)
        print(f"✓ Verification completed in {time.time() - ver_start:.2f}s")
        
        try:
            parsed_verification = json.loads(verification_output)
        except:
            try:
                json_match = re.search(r'\{[\s\S]*?\}', verification_output)
                if json_match:
                    parsed_verification = json.loads(json_match.group(0))
            except:
                parsed_verification = {
                    "pass_fail": "UNKNOWN",
                    "risk_score": 0.5,
                    "violated_requirements": [],
                    "explanation": "Could not parse verification",
                    "raw_output": verification_output
                }
        
        verification_result = parsed_verification
    
    print(f"✓ Total request: {time.time() - start_time:.2f}s")
    
    return {
        "query": question,
        "dss_output": dss_output,
        "context": context,
        "verification": verification_result,
        "conversation_length": len(conversations[session_id])
    }

@app.get("/ask")
def ask_get(q: str, session_id: str = "default", verify: bool = False):
    """
    Ask a question (GET - for backward compatibility)
    """
    # Convert GET to POST format
    request = ChatRequest(
        question=q,
        session_id=session_id,
        verify=verify
    )
    return ask(request)

@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Get conversation history for a session"""
    return {
        "session_id": session_id,
        "conversation": conversations.get(session_id, []),
        "uploaded_files": session_files.get(session_id, [])
    }

@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """Clear conversation history for a session"""
    if session_id in conversations:
        del conversations[session_id]
    if session_id in session_files:
        del session_files[session_id]
    return {"message": "History cleared", "session_id": session_id}

@app.get("/files")
def list_files():
    """List all uploaded files"""
    try:
        files = []
        for file in os.listdir(UPLOAD_DIR):
            if not os.path.isdir(os.path.join(UPLOAD_DIR, file)):
                file_path = os.path.join(UPLOAD_DIR, file)
                file_stat = os.stat(file_path)
                files.append({
                    "name": file,
                    "size": file_stat.st_size,
                    "modified": file_stat.st_mtime,
                    "extension": os.path.splitext(file)[1]
                })
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "files": []
        }

@app.get("/")
def home():
    return {
        "message": "RAG Verification API with Conversation Memory",
        "endpoints": {
            "POST /ask": "Ask questions (with history)",
            "POST /upload": "Upload files",
            "GET /history/{session_id}": "Get conversation history",
            "DELETE /history/{session_id}": "Clear history",
            "GET /files": "List all files"
        }
    }