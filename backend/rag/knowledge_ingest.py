from dotenv import load_dotenv
from pathlib import Path

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# ==========================================
# LOAD RCA KNOWLEDGE
# ==========================================

rca_text = Path(
    "data/rca_KB.txt"
).read_text(
    encoding="utf-8"
)

# ==========================================
# LOAD MAPPING KNOWLEDGE
# ==========================================

mapping_text = Path(
    "data/mapping_KB.txt"
).read_text(
    encoding="utf-8"
)

documents = []

# ==========================================
# RCA ENTRIES
# ==========================================

rca_entries = rca_text.split(
    "========================================================"
)

for entry in rca_entries:

    entry = entry.strip()

    if len(entry) > 50:

        documents.append(
            Document(
                page_content=entry,
                metadata={
                    "source": "rca"
                }
            )
        )

# ==========================================
# MAPPING DOCUMENT
# ==========================================

documents.append(
    Document(
        page_content=mapping_text,
        metadata={
            "source": "mapping"
        }
    )
)

print(f"Knowledge Documents: {len(documents)}")

# ==========================================
# EMBEDDINGS
# ==========================================

embeddings = HuggingFaceEmbeddings(
    model_name=r"C:\Users\sakthi murugan\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)

# ==========================================
# STORE IN CHROMA
# ==========================================

Chroma.from_documents(
    documents=documents,
    embedding=embeddings,
    collection_name="telecom_knowledge",
    persist_directory="vector_db"
)

print("Knowledge Base Indexed Successfully")

# ==========================================
# VERIFY DOCUMENTS
# ==========================================

print(f"\nKnowledge Documents: {len(documents)}")

print("\n" + "=" * 80)
print("SAMPLE DOCUMENTS")
print("=" * 80)

for i, doc in enumerate(documents[:3], start=1):

    print(f"\nDOCUMENT {i}")
    print("-" * 80)

    preview = doc.page_content[:500]

    print(preview)

    if len(doc.page_content) > 500:
        print("\n...TRUNCATED...")