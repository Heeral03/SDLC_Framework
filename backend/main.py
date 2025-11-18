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

UPLOAD_DIR = "./data/docs/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

conversations: Dict[str, List[Dict]] = {}
session_files: Dict[str, List[str]] = {}
session_timestamps: Dict[str, datetime] = {}
session_phases: Dict[str, str] = {}

class ChatRequest(BaseModel):
    question: str
    session_id: str
    verify: bool = False
    sdlc_phase: str = "auto"

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
    file_lower = filename.lower()
    content_lower = file_content.lower()
    
    if any(keyword in file_lower or keyword in content_lower for keyword in 
           ['requirement', 'srs', 'user story', 'use case', 'functional spec']):
        return "requirements"
    elif any(keyword in file_lower or keyword in content_lower for keyword in 
             ['design', 'architecture', 'uml', 'diagram', 'schema', 'erd']):
        return "design"
    elif any(keyword in file_lower or keyword in content_lower for keyword in 
             ['test', 'pytest', 'unittest', 'spec.', 'test_', '_test']):
        return "testing"
    elif any(keyword in file_lower or keyword in content_lower for keyword in 
             ['deploy', 'docker', 'kubernetes', 'ci/cd', 'pipeline', '.yml', '.yaml']):
        return "deployment"
    elif any(ext in file_lower for ext in ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs']):
        return "development"
    
    return "development"

def format_sdlc_response(raw_response: str, phase_name: str) -> str:
    import re
    
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', raw_response)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    output = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    output += f"SDLC EVALUATION: {phase_name.upper()}\n"
    output += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    current_section = None
    section_content = []
    
    section_keywords = {
        'analysis': ['ANALYSIS'],
        'phase_compliance': ['PHASE COMPLIANCE', 'COMPLIANCE'],
        'issues': ['ISSUES FOUND', 'ISSUES'],
        'recommendations': ['RECOMMENDATIONS'],
        'risk': ['RISK LEVEL', 'RISK'],
        'next_steps': ['NEXT STEPS'],
        'missing': ['MISSING INFORMATION', 'MISSING']
    }
    
    def is_section_header(line):
        line_upper = line.upper()
        for section_type, keywords in section_keywords.items():
            if any(keyword in line_upper for keyword in keywords):
                return section_type
        return None
    
    def format_section(section_name, content_lines):
        if not content_lines:
            return ""
        
        section_titles = {
            'analysis': '📋 ANALYSIS',
            'phase_compliance': '✓ PHASE COMPLIANCE',
            'issues': '⚠ ISSUES FOUND',
            'recommendations': '💡 RECOMMENDATIONS',
            'risk': '🎯 RISK LEVEL',
            'next_steps': '→ NEXT STEPS',
            'missing': '❓ MISSING INFORMATION'
        }
        
        result = f"\n{section_titles.get(section_name, section_name.upper())}\n"
        result += "─" * 50 + "\n"
        
        item_counter = 1
        for line in content_lines:
            line = line.strip()
            if not line:
                continue
            
            line = re.sub(r'^\d+\.\s*', '', line)
            line = re.sub(r'^[\*\-•]\s*', '', line)
            
            if section_name in ['issues', 'recommendations', 'next_steps', 'missing', 'phase_compliance']:
                result += f"{item_counter}. {line}\n"
                item_counter += 1
            else:
                result += f"{line}\n"
        
        return result + "\n"
    
    for line in lines:
        section_type = is_section_header(line)
        
        if section_type:
            if current_section and section_content:
                output += format_section(current_section, section_content)
            current_section = section_type
            section_content = []
        else:
            if current_section:
                section_content.append(line)
            else:
                output += line + "\n"
    
    if current_section and section_content:
        output += format_section(current_section, section_content)
    
    output += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return output

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = "default"):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        if session_id not in session_files:
            session_files[session_id] = []
        session_files[session_id].append(file.filename)
        
        session_timestamps[session_id] = datetime.now()
        
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
        
        file_content = docs[0].page_content if docs else ""
        detected_phase = detect_sdlc_phase(file_content, file.filename)
        session_phases[session_id] = detected_phase
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80
        )
        chunks = splitter.split_documents(docs)
        rag.db.add_documents(chunks)
        rag.db.persist()
        
        print(f"File uploaded: {file.filename} ({len(chunks)} chunks)")
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
    import time
    import json
    import re
    
    start_time = time.time()
    session_id = request.session_id
    question = request.question
    
    if session_id not in conversations:
        conversations[session_id] = []
    
    session_timestamps[session_id] = datetime.now()
    
    session_specific_files = session_files.get(session_id, [])
    
    if request.sdlc_phase != "auto":
        current_phase = request.sdlc_phase
    else:
        current_phase = session_phases.get(session_id, "development")
    
    phase_info = SDLC_PHASES.get(current_phase, SDLC_PHASES["development"])
    
    # Get RAG context
    if session_specific_files:
        context = rag.query(question, k=4, source_files=session_specific_files)
    else:
        context = rag.query(question, k=4)
    
    # Limit context to essential information only
    context_summary = context[:800] if context else "No relevant documents found."
    
    # Build conversation history (last 4 exchanges only)
    conversation_context = ""
    if conversations[session_id]:
        conversation_context = "\nRecent conversation:\n"
        for msg in conversations[session_id][-4:]:
            conversation_context += f"{msg['role']}: {msg['content'][:100]}...\n"
    
    files_context = ""
    if session_specific_files:
        files_context = f"Uploaded files: {', '.join(session_specific_files)}"
    
    # Optimized concise prompt
    dss_prompt = f"""You are an expert SDLC Decision Support System.

Phase: {phase_info['name']}
Description: {phase_info['description']}
Context: {files_context}
Relevant documents: {context_summary}
{conversation_context}

User question: {question}

Task:
1. Analyze the provided documents for the {phase_info['name']} phase
2. Verify against these criteria:
{chr(10).join(f"   - {criterion}" for criterion in phase_info['verification_criteria'])}
3. Identify specific issues and gaps
4. Provide clear, actionable recommendations
5. Determine risk level: Low, Medium, or High
6. List what additional information is needed (if any)

Output format (use these exact section headers):

ANALYSIS:
[2-3 sentences on current state and quality]

PHASE COMPLIANCE:
[For each criterion: MET/PARTIAL/NOT MET with brief reason]

ISSUES FOUND:
[List 3-5 specific issues or state "No critical issues found"]

RECOMMENDATIONS:
[List 4-6 actionable recommendations, prioritized]

RISK LEVEL:
[Low/Medium/High Risk with 2 sentence justification]

NEXT STEPS:
[List 4-6 prioritized action items]

MISSING INFORMATION:
[What additional artifacts/data are needed, or state "None"]

Be concise, specific, and actionable. Use numbered lists.

Response:"""
    
    print(f"Generating SDLC analysis...")
    gen_start = time.time()
    
    dss_output = slm.generate(dss_prompt, max_tokens=700)
    
    if "Response:" in dss_output:
        dss_output = dss_output.split("Response:")[-1].strip()
    
    formatted_output = format_sdlc_response(dss_output, phase_info['name'])
    
    print(f"Response generated in {time.time() - gen_start:.2f}s")
    
    conversations[session_id].append({
        "role": "user",
        "content": question
    })
    conversations[session_id].append({
        "role": "assistant",
        "content": formatted_output
    })
    
    # Verification (if enabled)
    verification_result = None
    if request.verify:
        print(f"Running compliance verification...")
        verification_prompt = f"""You are an SDLC Compliance Auditor.

Phase: {phase_info['name']}
Criteria: {', '.join(phase_info['verification_criteria'])}

Question: {question}
Response: {dss_output[:500]}

Return ONLY valid JSON:
{{
  "pass_fail": "PASS or FAIL",
  "compliance_score": 0.85,
  "criteria_met": ["criterion 1", "criterion 2"],
  "criteria_failed": ["criterion 3"],
  "risk_level": "Low/Medium/High",
  "recommendations": ["rec 1", "rec 2"],
  "explanation": "brief explanation"
}}"""
        
        ver_start = time.time()
        verification_output = slm.generate(verification_prompt, max_tokens=250)
        print(f"Verification completed in {time.time() - ver_start:.2f}s")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', verification_output)
            if json_match:
                parsed_verification = json.loads(json_match.group(0))
            else:
                parsed_verification = json.loads(verification_output)
        except:
            parsed_verification = {
                "pass_fail": "UNKNOWN",
                "compliance_score": 0.5,
                "criteria_met": [],
                "criteria_failed": [],
                "risk_level": "Medium",
                "recommendations": ["Manual review required"],
                "explanation": "Could not parse verification"
            }
        
        verification_result = parsed_verification
    
    print(f"Total request: {time.time() - start_time:.2f}s")
    
    return {
        "query": question,
        "dss_output": formatted_output,
        "verification": verification_result,
        "conversation_length": len(conversations[session_id]),
        "session_files": session_specific_files,
        "sdlc_phase": current_phase,
        "phase_info": phase_info
    }

@app.get("/ask")
def ask_get(q: str, session_id: str = "default", verify: bool = False, sdlc_phase: str = "auto"):
    request = ChatRequest(
        question=q,
        session_id=session_id,
        verify=verify,
        sdlc_phase=sdlc_phase
    )
    return ask(request)

@app.post("/set_phase/{session_id}")
def set_phase(session_id: str, phase: str):
    if phase not in SDLC_PHASES:
        return {
            "success": False,
            "message": f"Invalid phase. Valid: {list(SDLC_PHASES.keys())}"
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
    return {
        "phases": SDLC_PHASES,
        "total": len(SDLC_PHASES)
    }

@app.get("/history/{session_id}")
def get_history(session_id: str):
    return {
        "session_id": session_id,
        "conversation": conversations.get(session_id, []),
        "uploaded_files": session_files.get(session_id, []),
        "last_activity": session_timestamps.get(session_id),
        "current_phase": session_phases.get(session_id, "auto")
    }

@app.delete("/history/{session_id}")
def clear_history(session_id: str):
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
    import uuid
    new_session_id = str(uuid.uuid4())
    session_timestamps[new_session_id] = datetime.now()
    return {
        "session_id": new_session_id,
        "message": "New session created"
    }

@app.get("/cleanup")
def cleanup_old_sessions(hours: int = 24):
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
        "version": "4.0",
        "description": "Concise AI-powered SDLC verification and guidance",
        "features": [
            "Phase-aware analysis with structured output",
            "Automatic phase detection",
            "Compliance checking and risk assessment",
            "Concise, actionable recommendations"
        ],
        "sdlc_phases": list(SDLC_PHASES.keys()),
        "endpoints": {
            "POST /ask": "Ask questions with SDLC analysis",
            "POST /upload": "Upload files",
            "POST /set_phase/{session_id}": "Set SDLC phase",
            "GET /phases": "List SDLC phases",
            "POST /session/new": "Create session",
            "GET /history/{session_id}": "Get history",
            "DELETE /history/{session_id}": "Clear history",
            "GET /sessions": "List sessions",
            "GET /files": "List files"
        }
    }