import csv
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-2.0-flash-exp')

def load_faq(csv_file):
    faq_data = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        csv_reader = csv.reader(file, delimiter='\t')
        header = next(csv_reader)  # Skip header row
        for row in csv_reader:
            if len(row) >= 2:
                faq_data.append({'question': row[0], 'answer': row[1]})
            else:
                print(f"Skipping row with missing values: {row}")
    return faq_data

faq_data = load_faq('faq.csv')

def get_gemini_response(query):
    prompt = f"Answer the following question based on the provided FAQ:\nQuestion: {query}\nFAQ: {faq_data}"

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating response from Gemini API: {e}"

while True:
    user_query = input("Enter your question (or type 'exit' to quit): ")
    if user_query.lower() == 'exit':
        break

    gemini_response = get_gemini_response(user_query)
    print(f"Answer: {gemini_response}")
