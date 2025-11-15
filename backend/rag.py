import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, PDFPlumberLoader

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

    def load_docs(self, path="./data/docs/"):
        docs = []

        # Load all documents
        for file in os.listdir(path):
            full_path = os.path.join(path, file)

            if file.endswith(".txt"):
                loader = TextLoader(full_path)
            elif file.endswith(".pdf"):
                loader = PDFPlumberLoader(full_path)
            else:
                continue

            docs.extend(loader.load())

        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80
        )
        chunks = splitter.split_documents(docs)

        # Add to Chroma (embedding done automatically)
        self.db.add_documents(chunks)
        self.db.persist()

    def query(self, question):
        results = self.db.similarity_search(question, k=3)
        return "\n".join([doc.page_content for doc in results])
