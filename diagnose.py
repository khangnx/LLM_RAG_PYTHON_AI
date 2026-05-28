import sys
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Configure output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
VECTOR_DB_DIR = "./vector_db"

print("Connecting to Chroma...")
vector_store = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embeddings)

# Let's count how many documents are in the database
collection = vector_store._collection
count = collection.count()
print(f"Total documents in Chroma: {count}")

# Let's inspect some documents from products_debug.log
print("\nInspecting up to 5 documents from products_debug.log:")
results = collection.get(where={"file_name": "products_debug.log"}, limit=5)
for i, (doc_id, metadata, document) in enumerate(zip(results['ids'], results['metadatas'], results['documents'])):
    print(f"[{i+1}] ID: {doc_id}")
    print(f"    Metadata: {metadata}")
    print(f"    Content: {document[:150]}...")

# Run similarity search
query = "Tìm giúp tôi giá trị của product_code SP001"
print(f"\nRunning similarity search for query: '{query}'")
docs_and_scores = vector_store.similarity_search_with_score(query, k=5)
for i, (doc, score) in enumerate(docs_and_scores):
    print(f"[{i+1}] Score: {score:.4f}")
    print(f"    File: {doc.metadata.get('file_name')} | Row: {doc.metadata.get('row_index', 'N/A')}")
    print(f"    Content: {doc.page_content[:200]}...")
