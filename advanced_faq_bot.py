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
WC_URL = "https://wholesale.silkroademart.com"
WC_KEY = "ck_7f762d0bb0a2243c237d76fc21c1c4210b3c9453"
WC_SECRET = "cs_70dda921540d202bcdd980ddbeb8c7adb3f8d518"

class FAQDatabase:
    def __init__(self):
        self.conn = None
        self.model = Gemini(
            id="gemini-2.0-flash-exp",
            api_key=GEMINI_API_KEY,
            generative_model_kwargs={},
            generation_config={}
        )

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
        """Generate embedding for text using Gemini"""
        try:
            # Use the model to generate embeddings
            # Note: This is a simplified version. Actual implementation would depend on Gemini's embedding API
            response = self.model.get_embedding(text)
            return response
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def load_csv_data(self, csv_path: str):
        """Load FAQ data from CSV file"""
        try:
            df = pd.read_csv(csv_path)
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

class FAQBot:
    def __init__(self):
        self.db = FAQDatabase()
        self.agent = Agent(
            model=Gemini(
                id="gemini-2.0-flash-exp",
                api_key=GEMINI_API_KEY,
                generative_model_kwargs={},
                generation_config={}
            ),
            instructions="Answer user questions using the provided FAQ database and website content.",
            show_tool_calls=True,
            markdown=True,
        )

    def initialize(self):
        """Initialize the FAQ bot"""
        self.db.connect()
        self.db.initialize_database()
        
        # Load CSV data if it exists
        if os.path.exists('faq.csv'):
            self.db.load_csv_data('faq.csv')
        
        # Scrape website content
        self.db.scrape_website_content()

    def answer_question(self, query: str) -> str:
        """Generate answer for user query"""
        try:
            # Find similar questions from database
            similar_results = self.db.find_similar_questions(query)
            
            if not similar_results:
                # If no similar questions found, use Gemini to generate an answer
                response = self.agent.generate(
                    f"Please answer this question about wholesale.silkroademart.com: {query}"
                )
                return response
            
            # Combine similar results into context
            context = "\n".join([f"Q: {q}\nA: {a}" for q, a, _ in similar_results])
            
            # Generate answer using context
            prompt = f"""
            Based on the following similar questions and answers:
            {context}
            
            Please provide a comprehensive answer to: {query}
            """
            
            response = self.agent.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return "I apologize, but I encountered an error while processing your question. Please try again."

def display_menu():
    """Display the main menu options"""
    print("\n=== FAQ Bot Menu ===")
    print("1. Ask a Question")
    print("2. Reload FAQ Database")
    print("3. Update Website Content")
    print("4. Exit")
    return input("Enter your choice (1-4): ")

def main():
    bot = FAQBot()
    
    try:
        bot.initialize()
        logger.info("FAQ Bot initialized successfully")
        
        while True:
            choice = display_menu()
            
            if choice == '1':
                query = input("\nEnter your question: ")
                answer = bot.answer_question(query)
                print("\nAnswer:", answer)
                
            elif choice == '2':
                print("\nReloading FAQ database...")
                bot.db.load_csv_data('faq.csv')
                print("FAQ database reloaded successfully")
                
            elif choice == '3':
                print("\nUpdating website content...")
                bot.db.scrape_website_content()
                print("Website content updated successfully")
                
            elif choice == '4':
                print("\nExiting program...")
                break
                
            else:
                print("\nInvalid choice. Please select a number between 1 and 4.")
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        print("An error occurred. Please check the logs for details.")
    
    finally:
        if bot.db.conn:
            bot.db.conn.close()

if __name__ == "__main__":
    main()