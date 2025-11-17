from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from rag import RAGPipeline
from model import SLMModel
import os
import shutil
from typing import Dict, List
from pydantic import BaseModel
from datetime import datetime, timedelta

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
# Track session activity timestamps
session_timestamps: Dict[str, datetime] = {}
# Track SDLC phase per session
session_phases: Dict[str, str] = {}

class ChatRequest(BaseModel):
    question: str
    session_id: str
    verify: bool = False
    sdlc_phase: str = "auto"  # auto, requirements, design, development, testing, deployment, maintenance

# SDLC Phase Definitions
SDLC_PHASES = {
    "requirements": {
        "name": "Requirements Analysis",
        "description": "Gathering and documenting what the software should do",
        "verification_criteria": [
            "Are all functional requirements clearly defined?",
            "Are non-functional requirements (performance, security) specified?",
            "Are requirements testable and measurable?",
            "Are stakeholder needs properly captured?",
            "Is there proper requirements traceability?"
        ]
    },
    "design": {
        "name": "System Design",
        "description": "Creating architecture and detailed design specifications",
        "verification_criteria": [
            "Is the architecture scalable and maintainable?",
            "Are design patterns appropriately used?",
            "Is the database schema normalized and optimized?",
            "Are security considerations addressed in design?",
            "Is the design documented with proper diagrams (UML, ERD, etc.)?"
        ]
    },
    "development": {
        "name": "Implementation/Coding",
        "description": "Writing code according to design specifications",
        "verification_criteria": [
            "Does the code follow coding standards and best practices?",
            "Is the code properly commented and documented?",
            "Are error handling and logging implemented?",
            "Is the code modular and reusable?",
            "Are security vulnerabilities (SQL injection, XSS, etc.) prevented?"
        ]
    },
    "testing": {
        "name": "Testing & Quality Assurance",
        "description": "Verifying that software meets requirements and is defect-free",
        "verification_criteria": [
            "Are unit tests written and passing?",
            "Is integration testing performed?",
            "Are edge cases and error scenarios tested?",
            "Is test coverage adequate (>80%)?",
            "Are performance and security tests conducted?"
        ]
    },
    "deployment": {
        "name": "Deployment & Release",
        "description": "Moving software to production environment",
        "verification_criteria": [
            "Is the deployment process automated and documented?",
            "Are rollback procedures in place?",
            "Is monitoring and logging configured?",
            "Are environment configurations properly managed?",
            "Is the deployment checklist completed?"
        ]
    },
    "maintenance": {
        "name": "Maintenance & Support",
        "description": "Ongoing updates, bug fixes, and improvements",
        "verification_criteria": [
            "Are bugs tracked and prioritized properly?",
            "Is documentation kept up-to-date?",
            "Are performance metrics monitored?",
            "Is technical debt being addressed?",
            "Are user feedback and issues handled promptly?"
        ]
    }
}

def detect_sdlc_phase(file_content: str, filename: str) -> str:
    """Auto-detect SDLC phase based on file content and name"""
    file_lower = filename.lower()
    content_lower = file_content.lower()
    
    # Requirements indicators
    if any(keyword in file_lower or keyword in content_lower for keyword in 
           ['requirement', 'srs', 'user story', 'use case', 'functional spec']):
        return "requirements"
    
    # Design indicators
    elif any(keyword in file_lower or keyword in content_lower for keyword in 
             ['design', 'architecture', 'uml', 'diagram', 'schema', 'erd']):
        return "design"
    
    # Testing indicators
    elif any(keyword in file_lower or keyword in content_lower for keyword in 
             ['test', 'pytest', 'unittest', 'spec.', 'test_', '_test']):
        return "testing"
    
    # Deployment indicators
    elif any(keyword in file_lower or keyword in content_lower for keyword in 
             ['deploy', 'docker', 'kubernetes', 'ci/cd', 'pipeline', '.yml', '.yaml']):
        return "deployment"
    
    # Code/Development indicators
    elif any(ext in file_lower for ext in ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs']):
        return "development"
    
    # Default
    return "development"

def format_response_for_display(text: str) -> str:
    """
    Format the AI response to be more presentable by:
    - Converting asterisk points to numbered/bullet points
    - Removing markdown symbols
    - Ensuring proper paragraph structure
    - Cleaning up formatting artifacts
    """
    import re
    
    # Remove common markdown symbols but keep the structure
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Remove inline code
    text = re.sub(r'#+\s*', '', text)             # Remove headers
    
    # Convert various bullet styles to clean numbered lists
    lines = text.split('\n')
    formatted_lines = []
    in_list = False
    list_counter = 1
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines at the beginning of lists
        if not line and in_list:
            continue
            
        # Detect list items (various formats)
        list_match = re.match(r'^[\*\-•]\s+(.*)', line)
        numbered_match = re.match(r'^(\d+)\.?\s+(.*)', line)
        
        if list_match or numbered_match:
            if not in_list:
                in_list = True
                list_counter = 1
            
            if list_match:
                content = list_match.group(1)
            else:
                content = numbered_match.group(2)
                list_counter = int(numbered_match.group(1))
            
            formatted_lines.append(f"{list_counter}. {content}")
            list_counter += 1
            
        else:
            if in_list:
                in_list = False
                formatted_lines.append('')  # Add spacing after list
            
            if line:
                # Handle section headers
                if line.endswith(':') and len(line) < 50:
                    formatted_lines.append(f"\n{line.upper()}")
                else:
                    formatted_lines.append(line)
    
    # Join lines with proper spacing
    result = '\n'.join(formatted_lines)
    
    # Clean up multiple empty lines
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    
    # Ensure proper spacing around lists
    result = re.sub(r'(\S)\n(\d+\.)', r'\1\n\n\2', result)
    
    return result.strip()

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
        
        # Update session timestamp
        session_timestamps[session_id] = datetime.now()
        
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
        
        # Detect SDLC phase
        file_content = docs[0].page_content if docs else ""
        detected_phase = detect_sdlc_phase(file_content, file.filename)
        session_phases[session_id] = detected_phase
        
        # Split and add to vector store
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80
        )
        chunks = splitter.split_documents(docs)
        rag.db.add_documents(chunks)
        rag.db.persist()
        
        print(f"File uploaded: {file.filename} ({len(chunks)} chunks) for session {session_id}")
        print(f"Detected SDLC Phase: {detected_phase}")
        
        return {
            "success": True,
            "message": "File uploaded and processed successfully",
            "filename": file.filename,
            "chunks_created": len(chunks),
            "session_id": session_id,
            "session_files": session_files[session_id],
            "detected_sdlc_phase": detected_phase,
            "phase_info": SDLC_PHASES.get(detected_phase, {})
        }
    
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return {
            "success": False,
            "message": f"Error processing file: {str(e)}",
            "filename": file.filename
        }

@app.post("/ask")
def ask(request: ChatRequest):
    """
    Ask a question with SDLC-aware Decision Support System
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
    
    # Update session timestamp
    session_timestamps[session_id] = datetime.now()
    
    # Get session-specific files
    session_specific_files = session_files.get(session_id, [])
    
    # Determine SDLC phase
    if request.sdlc_phase != "auto":
        current_phase = request.sdlc_phase
    else:
        current_phase = session_phases.get(session_id, "development")
    
    phase_info = SDLC_PHASES.get(current_phase, SDLC_PHASES["development"])
    
    # Get relevant context from RAG - FILTERED by session files
    if session_specific_files:
        # Query only the files uploaded in this session
        context = rag.query(question, k=5, source_files=session_specific_files)
        print(f"RAG query (filtered to {len(session_specific_files)} files) completed in {time.time() - start_time:.2f}s")
    else:
        # No files uploaded yet - search all documents (fallback)
        context = rag.query(question, k=5)
        print(f"RAG query (all documents - no session files) completed in {time.time() - start_time:.2f}s")
    
    # Build conversation history
    conversation_context = ""
    if conversations[session_id]:
        conversation_context = "\n\nPrevious conversation:\n"
        # Only include last 3 exchanges to keep prompt short
        for msg in conversations[session_id][-6:]:  # 3 Q&A pairs
            conversation_context += f"{msg['role']}: {msg['content']}\n"
    
    # Add uploaded files context
    files_context = ""
    if session_specific_files:
        files_context = f"\n\nFiles in this session: {', '.join(session_specific_files)}"
    
    # SDLC-Aware Decision Support System Prompt
    dss_prompt = f"""You are an expert Software Development Life Cycle (SDLC) Decision Support System.

CURRENT SDLC PHASE
Phase: {phase_info['name']}
Description: {phase_info['description']}

VERIFICATION CRITERIA FOR THIS PHASE
{chr(10).join(f"{i+1}. {criterion}" for i, criterion in enumerate(phase_info['verification_criteria']))}

{files_context}

CONTEXT FROM UPLOADED DOCUMENTS
{context}
{conversation_context}

USER QUESTION
{question}

YOUR ROLE AS DSS
As a Decision Support System for SDLC, you must:

1. Analyze the uploaded documents in the context of the current SDLC phase ({phase_info['name']})

2. Verify against the phase-specific criteria listed above

3. Identify Issues:
   - Missing requirements or documentation
   - Best practice violations
   - Security vulnerabilities
   - Performance concerns
   - Compliance gaps

4. Provide Recommendations:
   - Specific, actionable improvements
   - Industry best practices
   - Risk mitigation strategies
   - Next steps for this phase

5. Reference Context: Use conversation history for context (e.g., "this file", "the code")

6. Be Honest: If you cannot verify something from the provided context, clearly state what additional information is needed

OUTPUT FORMAT
Provide a structured response with these sections:

ANALYSIS
Provide a clear analysis of what you found in the documents

PHASE COMPLIANCE
Evaluate how well the current state meets {phase_info['name']} criteria

ISSUES FOUND
List specific problems identified, if any

RECOMMENDATIONS
Provide actionable improvement suggestions

RISK LEVEL
Assess the risk level: Low, Medium, or High

NEXT STEPS
Outline what should be done next

Use clear, professional language without markdown formatting. Use numbered lists and proper paragraphs.

Answer:"""
    
    print(f"Generating SDLC-aware response... (this may take 10-20 seconds)")
    gen_start = time.time()
    
    # Generate response with appropriate length for analysis
    dss_output = slm.generate(dss_prompt, max_tokens=400)
    
    # Extract just the answer (remove the prompt echo)
    answer_marker = "Answer:"
    if answer_marker in dss_output:
        dss_output = dss_output.split(answer_marker)[-1].strip()
    
    # Format the response for clean display
    formatted_output = format_response_for_display(dss_output)
    
    print(f"Response generated in {time.time() - gen_start:.2f}s")
    
    # Store conversation history
    conversations[session_id].append({
        "role": "user",
        "content": question
    })
    conversations[session_id].append({
        "role": "assistant",
        "content": formatted_output  # Store formatted version
    })
    
    # SDLC-Specific Verification
    verification_result = None
    if request.verify:
        print(f"Running SDLC compliance verification...")
        verification_prompt = f"""
You are an SDLC Compliance Auditor. Verify this response against {phase_info['name']} standards.

SDLC Phase: {phase_info['name']}
Phase Criteria:
{chr(10).join(f"- {criterion}" for criterion in phase_info['verification_criteria'])}

Question: {question}
DSS Answer: {formatted_output}

Evaluate and return JSON ONLY:
{{
  "pass_fail": "PASS or FAIL",
  "compliance_score": 0.0-1.0,
  "phase_alignment": "How well the response aligns with {current_phase} phase",
  "criteria_met": ["list of criteria that are satisfied"],
  "criteria_failed": ["list of criteria that are not satisfied"],
  "risk_level": "Low/Medium/High",
  "security_concerns": ["any security issues identified"],
  "recommendations": ["specific improvements needed"],
  "explanation": "Brief explanation of the verification result"
}}
"""
        
        ver_start = time.time()
        verification_output = slm.generate(verification_prompt, max_tokens=300)
        print(f"Verification completed in {time.time() - ver_start:.2f}s")
        
        try:
            # Try to parse JSON
            json_match = re.search(r'\{[\s\S]*\}', verification_output)
            if json_match:
                parsed_verification = json.loads(json_match.group(0))
            else:
                parsed_verification = json.loads(verification_output)
        except:
            parsed_verification = {
                "pass_fail": "UNKNOWN",
                "compliance_score": 0.5,
                "phase_alignment": "Could not evaluate",
                "criteria_met": [],
                "criteria_failed": [],
                "risk_level": "Medium",
                "security_concerns": [],
                "recommendations": ["Manual review required"],
                "explanation": "Could not parse verification output",
                "raw_output": verification_output
            }
        
        verification_result = parsed_verification
    
    print(f"Total request: {time.time() - start_time:.2f}s")
    
    return {
        "query": question,
        "dss_output": formatted_output,  # Return formatted version
        "context": context,
        "verification": verification_result,
        "conversation_length": len(conversations[session_id]),
        "session_files": session_specific_files,
        "filtered_search": bool(session_specific_files),
        "sdlc_phase": current_phase,
        "phase_info": phase_info
    }

@app.get("/ask")
def ask_get(q: str, session_id: str = "default", verify: bool = False, sdlc_phase: str = "auto"):
    """
    Ask a question (GET - for backward compatibility)
    """
    request = ChatRequest(
        question=q,
        session_id=session_id,
        verify=verify,
        sdlc_phase=sdlc_phase
    )
    return ask(request)

@app.post("/set_phase/{session_id}")
def set_phase(session_id: str, phase: str):
    """Manually set SDLC phase for a session"""
    if phase not in SDLC_PHASES:
        return {
            "success": False,
            "message": f"Invalid phase. Valid phases: {list(SDLC_PHASES.keys())}"
        }
    
    session_phases[session_id] = phase
    return {
        "success": True,
        "session_id": session_id,
        "phase": phase,
        "phase_info": SDLC_PHASES[phase]
    }

@app.get("/phases")
def list_phases():
    """List all SDLC phases and their criteria"""
    return {
        "phases": SDLC_PHASES,
        "total": len(SDLC_PHASES)
    }

@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Get conversation history for a session"""
    return {
        "session_id": session_id,
        "conversation": conversations.get(session_id, []),
        "uploaded_files": session_files.get(session_id, []),
        "last_activity": session_timestamps.get(session_id),
        "current_phase": session_phases.get(session_id, "auto")
    }

@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """Clear conversation history for a session"""
    if session_id in conversations:
        del conversations[session_id]
    if session_id in session_files:
        del session_files[session_id]
    if session_id in session_timestamps:
        del session_timestamps[session_id]
    if session_id in session_phases:
        del session_phases[session_id]
    return {
        "message": "History cleared", 
        "session_id": session_id
    }

@app.delete("/session/{session_id}/files")
def clear_session_files(session_id: str):
    """Clear uploaded files tracking for a session"""
    if session_id in session_files:
        del session_files[session_id]
    if session_id in session_phases:
        del session_phases[session_id]
    return {
        "message": f"Session file tracking cleared for {session_id}",
        "session_id": session_id
    }

@app.post("/session/new")
def create_new_session():
    """Create a new session with a unique ID"""
    import uuid
    new_session_id = str(uuid.uuid4())
    session_timestamps[new_session_id] = datetime.now()
    return {
        "session_id": new_session_id,
        "message": "New session created"
    }

@app.get("/cleanup")
def cleanup_old_sessions(hours: int = 24):
    """Remove sessions older than X hours"""
    cutoff = datetime.now() - timedelta(hours=hours)
    expired = [sid for sid, ts in session_timestamps.items() if ts < cutoff]
    
    for sid in expired:
        if sid in conversations:
            del conversations[sid]
        if sid in session_files:
            del session_files[sid]
        if sid in session_timestamps:
            del session_timestamps[sid]
        if sid in session_phases:
            del session_phases[sid]
    
    return {
        "cleaned_sessions": len(expired),
        "cutoff_hours": hours,
        "remaining_sessions": len(session_timestamps)
    }

@app.get("/sessions")
def list_sessions():
    """List all active sessions"""
    sessions_info = []
    for sid in session_timestamps:
        sessions_info.append({
            "session_id": sid,
            "last_activity": session_timestamps.get(sid),
            "message_count": len(conversations.get(sid, [])),
            "uploaded_files": session_files.get(sid, []),
            "current_phase": session_phases.get(sid, "auto")
        })
    return {
        "sessions": sessions_info,
        "total": len(sessions_info)
    }

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
        "message": "SDLC Decision Support System (DSS) with RAG",
        "version": "3.0",
        "description": "AI-powered system to verify and guide software development across SDLC phases",
        "features": [
            "SDLC phase-aware analysis",
            "Automatic phase detection from uploaded files",
            "Phase-specific verification criteria",
            "Session-based file filtering",
            "Compliance checking and risk assessment",
            "Best practice recommendations"
        ],
        "sdlc_phases": list(SDLC_PHASES.keys()),
        "endpoints": {
            "POST /ask": "Ask questions with SDLC-aware analysis",
            "POST /upload": "Upload files (auto-detects SDLC phase)",
            "POST /set_phase/{session_id}": "Manually set SDLC phase",
            "GET /phases": "List all SDLC phases and criteria",
            "POST /session/new": "Create new session",
            "GET /history/{session_id}": "Get conversation history",
            "DELETE /history/{session_id}": "Clear session history",
            "GET /sessions": "List all active sessions",
            "GET /files": "List all files"
        }
    }