from agno.agent import Agent
from agno.models.google.gemini import Gemini
import os
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from bs4 import BeautifulSoup
from pgvector.psycopg2 import register_vector
import re
from typing import List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DB_NAME = os.getenv('DB_NAME', 'faq_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# WooCommerce credentials
WC_URL = os.getenv('WC_URL')
WC_KEY = os.getenv('WC_KEY')
WC_SECRET = os.getenv('WC_SECRET')

class FAQDatabase:
    def __init__(self):
        self.conn = None
        # Initialize the Gemini model properly with embedding capability
        self.model = Gemini(
            id="gemini-2.0-flash-exp",
            api_key=GEMINI_API_KEY,
            generative_model_kwargs={},
            generation_config={}
        )
        # Initialize the embedding client separately
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self.embedding_model = genai.GenerativeModel("embedding-001")
            logger.info("Successfully initialized embedding model")
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            self.embedding_model = None

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            register_vector(self.conn)
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    def initialize_database(self):
        """Create necessary tables if they don't exist"""
        try:
            with self.conn.cursor() as cur:
                # Create FAQ table with vector support
                cur.execute("""
                CREATE TABLE IF NOT EXISTS faqs (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    embedding vector(768),
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Create table for website content
                cur.execute("""
                CREATE TABLE IF NOT EXISTS website_content (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                self.conn.commit()
                logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            self.conn.rollback()
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Google's embedding model"""
        try:
            if self.embedding_model is None:
                # Fallback to a simple mock embedding if the model isn't available
                logger.warning("Using fallback mock embedding as embedding model is not available")
                # Create a deterministic but unique embedding based on the text
                import hashlib
                hash_obj = hashlib.md5(text.encode())
                hash_bytes = hash_obj.digest()
                # Create a 768-dimensional vector from the hash
                mock_embedding = []
                for i in range(768):
                    # Use modulo to get values between -1 and 1
                    val = ((hash_bytes[i % 16] / 128.0) - 1.0) * 0.1
                    mock_embedding.append(val)
                return mock_embedding
            
            # Use the embedding model to generate embeddings
            result = self.embedding_model.embed_content(text=text)
            return result.embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a zero vector as fallback
            return [0.0] * 768

    # Rest of the class methods remain the same
    def load_csv_data(self, csv_path: str):
        """Load FAQ data from CSV file"""
        try:
            df = pd.read_csv(csv_path, sep='\t')
            with self.conn.cursor() as cur:
                for _, row in df.iterrows():
                    question = row['question']
                    answer = row['answer']
                    embedding = self.generate_embedding(question)
                    
                    cur.execute("""
                    INSERT INTO faqs (question, answer, embedding, source)
                    VALUES (%s, %s, %s, %s)
                    """, (question, answer, embedding, 'csv'))
                
                self.conn.commit()
            logger.info(f"Successfully loaded data from {csv_path}")
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            self.conn.rollback()
            raise

    def scrape_website_content(self):
        """Scrape content from the website"""
        try:
            response = requests.get(WC_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find FAQ or help-related content
            faq_content = []
            faq_sections = soup.find_all(['div', 'section'], 
                class_=lambda x: x and ('faq' in x.lower() or 'help' in x.lower()))
            
            for section in faq_sections:
                text = section.get_text(strip=True)
                url = response.url
                embedding = self.generate_embedding(text)
                
                faq_content.append({
                    'url': url,
                    'content': text,
                    'embedding': embedding
                })
            
            # Store in database
            with self.conn.cursor() as cur:
                for content in faq_content:
                    cur.execute("""
                    INSERT INTO website_content (url, content, embedding)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (url) DO UPDATE
                    SET content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        last_updated = CURRENT_TIMESTAMP
                    """, (content['url'], content['content'], content['embedding']))
            
            self.conn.commit()
            logger.info("Successfully scraped and stored website content")
        except Exception as e:
            logger.error(f"Error scraping website: {e}")
            self.conn.rollback()
            raise

    def find_similar_questions(self, query: str, limit: int = 3) -> List[Tuple[str, str, float]]:
        """Find similar questions using vector similarity"""
        try:
            query_embedding = self.generate_embedding(query)
            
            with self.conn.cursor() as cur:
                # Search in FAQs table
                cur.execute("""
                SELECT question, answer, 1 - (embedding <=> %s) as similarity
                FROM faqs
                WHERE 1 - (embedding <=> %s) > 0.7
                ORDER BY similarity DESC
                LIMIT %s
                """, (query_embedding, query_embedding, limit))
                
                results = cur.fetchall()
                
                # Search in website content
                cur.execute("""
                SELECT content, url, 1 - (embedding <=> %s) as similarity
                FROM website_content
                WHERE 1 - (embedding <=> %s) > 0.7
                ORDER BY similarity DESC
                LIMIT %s
                """, (query_embedding, query_embedding, limit))
                
                website_results = cur.fetchall()
                
                return results + website_results
        except Exception as e:
            logger.error(f"Error finding similar questions: {e}")
            return []

# The rest of the file remains unchanged