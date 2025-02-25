import os
import csv
from dotenv import load_dotenv
import google.generativeai as genai
from agno.agent import Agent
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.vectordb.lancedb import LanceDb
from agno.embedder.google import GeminiEmbedder
from agno.models.google.gemini import Gemini

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Configure the Gemini API
genai.configure(api_key=gemini_api_key)
model = Gemini(id="gemini-1.5-pro-latest")

# Define the database URL where the vector database will be stored
db_url = "/tmp/lancedb"

# Configure the embedding model
embedder = GeminiEmbedder(id="embedding-001", dimensions=768)

# Create the vector database
vector_db = LanceDb(
    table_name="faq",  # Table name in the vector database
    uri=db_url,  # Location to initiate/create the vector database
    embedder=embedder,
)

# Read data from faq.csv
faq_data = []
with open("faq.csv", "r", encoding="utf-8") as csvfile:
    csv_reader = csv.DictReader(csvfile, delimiter='\t', quotechar='"')
    for row in csv_reader:
        faq_data.append(row)

from agno.knowledge.pdf_url import PDFUrlKnowledgeBase

from typing import List, Dict
from pydantic import Field
from agno.document import Document

class FaqKnowledgeBase(PDFUrlKnowledgeBase):
    faq_data: List[Dict[str, str]] = Field(default_factory=list)

    def __init__(self, vector_db: LanceDb, faq_data: List[Dict[str, str]], **kwargs):
        super().__init__(urls=[], vector_db=vector_db, **kwargs)
        self.faq_data = faq_data

    def load(self, recreate=False):
        if recreate:
            self.vector_db.delete()
        
        # Prepare data for LanceDB
        data = [Document(content=row["question"]) for row in self.faq_data]
        for i, row in enumerate(self.faq_data):
            data[i].metadata = {"answer": row["answer"]}
        
        # Add data to LanceDB
        self.vector_db.insert(data)


knowledge_base = FaqKnowledgeBase(vector_db=vector_db, faq_data=faq_data)
knowledge_base.load(recreate=True)

# Set up SQL storage for the agent's data
storage = SqliteAgentStorage(table_name="faq", db_file="data.db")
storage.create()  # Create the storage if it doesn't exist

# Initialize the Agent with various configurations including the knowledge base and storage
agent = Agent(
    session_id="session_id",  # use any unique identifier to identify the run
    user_id="user",  # user identifier to identify the user
    model=model,
    knowledge=knowledge_base,
    storage=storage,
    show_tool_calls=True,
    debug_mode=True,  # Enable debug mode for additional information
)

import io
import sys

# Use the agent to generate and print a response to a query, formatted in Markdown
captured_output = io.StringIO()
sys.stdout = captured_output
agent.print_response(
    "What is the return policy?",
    markdown=True,
)
sys.stdout = sys.__stdout__
response = captured_output.getvalue()
print(response)
