import json
import os
import pickle
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader, PDFPlumberLoader
from langchain.docstore.document import Document

class RAGPipeline:
    def __init__(self):
        # Correct embedder
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Correct Chroma initialization
        self.db = Chroma(
            collection_name="rag",
            embedding_function=self.embedding,
            persist_directory="./chroma_db"
        )

    def load_python_file(self, file_path):
        """Load Python files (.py)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path, "type": "python"})]

    def load_ipynb_file(self, file_path):
        """Load Jupyter Notebook files (.ipynb)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        # Extract all cells content
        content_parts = []
        for cell in notebook.get('cells', []):
            cell_type = cell.get('cell_type', '')
            source = ''.join(cell.get('source', []))
            
            if cell_type == 'code':
                content_parts.append(f"CODE CELL:\n{source}\n")
            elif cell_type == 'markdown':
                content_parts.append(f"MARKDOWN:\n{source}\n")
        
        content = '\n'.join(content_parts)
        return [Document(page_content=content, metadata={"source": file_path, "type": "jupyter"})]

    def load_json_file(self, file_path):
        """Load JSON files (.json)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        content = json.dumps(data, indent=2)
        return [Document(page_content=content, metadata={"source": file_path, "type": "json"})]

    def load_csv_file(self, file_path):
        """Load CSV files (.csv)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path, "type": "csv"})]

    def load_markdown_file(self, file_path):
        """Load Markdown files (.md)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path, "type": "markdown"})]

    def load_yaml_file(self, file_path):
        """Load YAML files (.yaml, .yml)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path, "type": "yaml"})]

    def load_code_file(self, file_path, language):
        """Load generic code files (js, java, cpp, etc.)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path, "type": language})]

    def load_pytorch_model_info(self, file_path):
        """Load PyTorch model files (.pt, .pth) - extracts metadata only"""
        try:
            import torch
            # Load model metadata without loading full weights
            checkpoint = torch.load(file_path, map_location='cpu')
            
            info_parts = [f"PyTorch Model: {os.path.basename(file_path)}"]
            
            if isinstance(checkpoint, dict):
                info_parts.append(f"Keys: {list(checkpoint.keys())}")
                
                # Extract model architecture info if available
                if 'model_state_dict' in checkpoint or 'state_dict' in checkpoint:
                    state_dict = checkpoint.get('model_state_dict') or checkpoint.get('state_dict')
                    info_parts.append(f"Number of parameters: {len(state_dict)}")
                    info_parts.append(f"Layer names: {list(state_dict.keys())[:10]}...")
                
                # Extract training metadata
                if 'epoch' in checkpoint:
                    info_parts.append(f"Epoch: {checkpoint['epoch']}")
                if 'optimizer_state_dict' in checkpoint:
                    info_parts.append("Contains optimizer state")
            
            content = '\n'.join(info_parts)
            return [Document(page_content=content, metadata={"source": file_path, "type": "pytorch_model"})]
        except Exception as e:
            # If PyTorch not available or file can't be loaded
            content = f"PyTorch Model File: {os.path.basename(file_path)}\nNote: Model metadata could not be extracted. Error: {str(e)}"
            return [Document(page_content=content, metadata={"source": file_path, "type": "pytorch_model"})]

    def load_pickle_file(self, file_path):
        """Load pickle files (.pkl, .pickle) - extracts basic info"""
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            content = f"Pickle File: {os.path.basename(file_path)}\n"
            content += f"Type: {type(data).__name__}\n"
            
            if isinstance(data, (list, tuple)):
                content += f"Length: {len(data)}\n"
            elif isinstance(data, dict):
                content += f"Keys: {list(data.keys())}\n"
            
            # Convert to string representation (limited)
            content += f"Content preview: {str(data)[:500]}..."
            
            return [Document(page_content=content, metadata={"source": file_path, "type": "pickle"})]
        except Exception as e:
            content = f"Pickle File: {os.path.basename(file_path)}\nNote: Could not load pickle file. Error: {str(e)}"
            return [Document(page_content=content, metadata={"source": file_path, "type": "pickle"})]

    def load_docs(self, path="./data/docs/"):
        docs = []
        
        # Supported file extensions mapping
        loaders = {
            '.txt': lambda f: TextLoader(f).load(),
            '.pdf': lambda f: PDFPlumberLoader(f).load(),
            '.py': self.load_python_file,
            '.ipynb': self.load_ipynb_file,
            '.json': self.load_json_file,
            '.csv': self.load_csv_file,
            '.md': self.load_markdown_file,
            '.yaml': self.load_yaml_file,
            '.yml': self.load_yaml_file,
            '.pt': self.load_pytorch_model_info,
            '.pth': self.load_pytorch_model_info,
            '.pkl': self.load_pickle_file,
            '.pickle': self.load_pickle_file,
            '.js': lambda f: self.load_code_file(f, 'javascript'),
            '.jsx': lambda f: self.load_code_file(f, 'javascript'),
            '.ts': lambda f: self.load_code_file(f, 'typescript'),
            '.tsx': lambda f: self.load_code_file(f, 'typescript'),
            '.java': lambda f: self.load_code_file(f, 'java'),
            '.cpp': lambda f: self.load_code_file(f, 'cpp'),
            '.c': lambda f: self.load_code_file(f, 'c'),
            '.h': lambda f: self.load_code_file(f, 'c'),
            '.rs': lambda f: self.load_code_file(f, 'rust'),
            '.go': lambda f: self.load_code_file(f, 'go'),
            '.rb': lambda f: self.load_code_file(f, 'ruby'),
            '.php': lambda f: self.load_code_file(f, 'php'),
            '.html': lambda f: self.load_code_file(f, 'html'),
            '.css': lambda f: self.load_code_file(f, 'css'),
            '.xml': lambda f: self.load_code_file(f, 'xml'),
            '.sh': lambda f: self.load_code_file(f, 'shell'),
            '.r': lambda f: self.load_code_file(f, 'r'),
            '.sql': lambda f: self.load_code_file(f, 'sql'),
        }

        # Load all documents
        for file in os.listdir(path):
            full_path = os.path.join(path, file)
            
            # Skip directories
            if os.path.isdir(full_path):
                continue
            
            # Get file extension
            _, ext = os.path.splitext(file)
            ext = ext.lower()
            
            # Load file if extension is supported
            if ext in loaders:
                try:
                    print(f"Loading {file}...")
                    loaded_docs = loaders[ext](full_path)
                    docs.extend(loaded_docs)
                    print(f"✓ Successfully loaded {file}")
                except Exception as e:
                    print(f"✗ Error loading {file}: {str(e)}")
            else:
                print(f"⊘ Skipping {file} (unsupported format: {ext})")

        print(f"\nTotal documents loaded: {len(docs)}")

        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80
        )
        chunks = splitter.split_documents(docs)
        print(f"Split into {len(chunks)} chunks")

        # Add to Chroma (embedding done automatically)
        self.db.add_documents(chunks)
        self.db.persist()
        print("✓ Documents embedded and persisted to Chroma DB")

    def query(self, question, k=5):
        """
        Query the vector database with metadata
        k: number of results to return (increased to 5 for better context)
        """
        results = self.db.similarity_search(question, k=k)
        
        # Format results with metadata
        formatted_results = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get('source', 'Unknown')
            doc_type = doc.metadata.get('type', 'Unknown')
            
            formatted_results.append(
                f"--- Document {i} (Source: {os.path.basename(source)}, Type: {doc_type}) ---\n"
                f"{doc.page_content}\n"
            )
        
        return "\n".join(formatted_results)