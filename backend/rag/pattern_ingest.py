import pandas as pd

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ==========================================
# LOAD CSV
# ==========================================

df = pd.read_csv("data/combined_data.csv")

print(f"Rows Found: {len(df)}")

# ==========================================
# CREATE DOCUMENTS
# ==========================================

documents = []

for _, row in df.iterrows():

    content = f"""
Incident ID: {row['id']}

Severity Category:
{row['severity_category']}

Event Categories:
{row['event_categories']}

Resource Categories:
{row['resource_categories']}

Log Feature Groups:
{row['log_feature_groups']}

Event Count:
{row['event_count']}

Total Log Volume:
{row['total_log_volume']}

Mean Log Volume:
{row['mean_log_volume']}

Unique Log Features:
{row['unique_log_features']}

Historical Root Cause:
{row['root_cause_description']}

Historical Solution:
{row['solution_description']}
"""

    documents.append(
        Document(
            page_content=content,
            metadata={
                "incident_id": int(row["id"])
            }
        )
    )

print(f"Pattern Documents: {len(documents)}")

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
    collection_name="telecom_patterns",
    persist_directory="vector_db"
)

print("Pattern Database Indexed Successfully")