import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
import logging
import openai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'API')
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
        openai.api_key = OPENROUTER_API_KEY
        openai.api_base = "https://openrouter.ai/api/v1"

    def connect(self):
        """Establish database connection"""
        print("Attempting database connection...")
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
            print("Database connection successful!")
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
                    embedding vector(1536),
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
                    embedding vector(1536),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                try:
                    self.conn.commit()
                    logger.info("Database tables initialized successfully")
                except Exception as e:
                    logger.error(f"Database initialization error: {e}")
                    self.conn.rollback()
                    raise

    def generate_embedding(self, text: str):
        """Generate embedding for text using OpenAI's embedding model via OpenRouter"""
        try:
            response = openai.embeddings.create(
                model="mistralai/Mistral-Embed",  # Choose a free model
                input=text,
                headers={
                    "HTTP-Referer": "https://agno_chatbot.com",  # Optional, but recommended
                    "X-Title": "Agno Chatbot"  # Optional, but recommended
                }
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 1536

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

    def find_similar_questions(self, query: str, limit: int = 3):
        """Find similar questions using vector similarity"""
        try:
            query_embedding = self.generate_embedding(query)
            
            with self.conn.cursor() as cur:
                cur.execute("""
                SELECT question, answer, 1 - (embedding <=> %s) as similarity
                FROM faqs
                ORDER BY similarity DESC
                LIMIT %s
                """, (query_embedding, limit))
                
                results = cur.fetchall()
                return results
        except Exception as e:
            logger.error(f"Error finding similar questions: {e}")
            return []

if __name__ == "__main__":
    db = FAQDatabase()
    db.connect()
    db.initialize_database()
    db.load_csv_data('faq.csv')
    db.scrape_website_content()
