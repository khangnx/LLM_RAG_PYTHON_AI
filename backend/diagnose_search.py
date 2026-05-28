import sys
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

sys.stdout.reconfigure(encoding='utf-8')
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = Chroma(persist_directory="/vector_db", embedding_function=embeddings)

query = "Cho tôi biết mẹ Thảo là ai"
docs = vector_store.similarity_search(query, k=10)
print(f"Top {len(docs)} documents for query: {query}\n")
for i, doc in enumerate(docs):
    print(f"--- Doc {i+1} (Source: {doc.metadata.get('source', 'Unknown')}) ---")
    print(doc.page_content[:200])
    print()
