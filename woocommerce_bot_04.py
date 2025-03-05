from agno.agent import Agent
from agno.models.google.gemini import Gemini
import os
from dotenv import load_dotenv
import csv
import mysql.connector
import gradio as gr
import re

load_dotenv()

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Database credentials
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
WC_URL = os.getenv("WC_URL")

# Check if all required environment variables are set
if not GEMINI_API_KEY or not DB_NAME or not DB_USER or not DB_PASSWORD or not DB_HOST or not WC_URL:
    raise ValueError("Missing required environment variables")

def load_faq(csv_file):
    """Load FAQ data from a CSV file"""
    faq_data = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file, delimiter='\t')
            header = next(csv_reader)  # Skip header row
            for row in csv_reader:
                if len(row) >= 2:
                    faq_data.append({'question': row[0], 'answer': row[1]})
                else:
                    print(f"Skipping row with missing values: {row}")
        return faq_data
    except FileNotFoundError:
        print(f"Error: FAQ file '{csv_file}' not found.")
        return []
    except Exception as e:
        print(f"Error loading FAQ data: {e}")
        return []

def get_order_status(email: str = None, order_id: str = None) -> str:
    """Tool to retrieve order status based on email or order ID"""
    if not email and not order_id:
        return "Please provide either an email address or order ID."
    
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        mycursor = mydb.cursor(dictionary=True)

        # Construct the SQL query to retrieve the order status
        query = """
        SELECT
            p.ID as order_id,
            p.post_status as order_status,
            p.post_date as order_date,
            MAX(CASE WHEN pm.meta_key = '_billing_first_name' THEN pm.meta_value END) as first_name,
            MAX(CASE WHEN pm.meta_key = '_billing_last_name' THEN pm.meta_value END) as last_name,
            MAX(CASE WHEN pm.meta_key = '_order_total' THEN pm.meta_value END) as total
        FROM
            wp_posts p
        JOIN wp_postmeta pm ON p.ID = pm.post_id
        WHERE
            p.post_type = 'shop_order'
        """
        
        params = []
        if order_id:
            query += " AND p.ID = %s"
            params.append(order_id)
        if email:
            query += " AND p.ID IN (SELECT post_id FROM wp_postmeta WHERE meta_key = '_billing_email' AND meta_value = %s)"
            params.append(email)
            
        query += " GROUP BY p.ID ORDER BY p.post_date DESC LIMIT 5"
        
        mycursor.execute(query, params)
        myresult = mycursor.fetchall()
        
        if myresult:
            result = ["Here are the order details:"]
            for row in myresult:
                order_date = row['order_date'].strftime('%Y-%m-%d %H:%M:%S') if row['order_date'] else 'N/A'
                status_mapping = {
                    'wc-pending': 'Pending payment',
                    'wc-processing': 'Processing',
                    'wc-on-hold': 'On hold',
                    'wc-completed': 'Completed',
                    'wc-cancelled': 'Cancelled',
                    'wc-refunded': 'Refunded',
                    'wc-failed': 'Failed'
                }
                status = status_mapping.get(row['order_status'], row['order_status'])
                
                result.append(f"Order #{row['order_id']}")
                result.append(f"Date: {order_date}")
                result.append(f"Customer: {row.get('first_name', '')} {row.get('last_name', '')}")
                result.append(f"Total: ${row.get('total', 'N/A')}")
                result.append(f"Status: {status}")
                result.append("---")
            
            return "\n".join(result)
        else:
            if order_id:
                return f"No order found with ID {order_id}."
            else:
                return f"No orders found for email {email}."

    except mysql.connector.Error as e:
        return f"Database error: {e}"
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        if 'mydb' in locals() and mydb:
            mydb.close()

def search_products(product_name: str) -> str:
    """Tool to search for products by name"""
    if not product_name:
        return "Please provide a product name to search for."
    
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        mycursor = mydb.cursor()

        # Use parameterized query for security
        query = """
        SELECT
            ID,
            post_title
        FROM
            wp_posts
        WHERE
            post_type = 'product'
            AND post_status = 'publish'
            AND post_title LIKE %s
        LIMIT 10;
        """
        
        # Add wildcards for the LIKE query
        search_term = f"%{product_name}%"
        mycursor.execute(query, (search_term,))
        
        myresult = mycursor.fetchall()
        
        if myresult:
            result = ["Here are the products that match your search:"]
            for row in myresult:
                product_id = row[0]
                product_title = row[1]
                product_link = f"{WC_URL}/product/{product_title.lower().replace(' ', '-')}"
                result.append(f"Product: {product_title}")
                result.append(f"Link: {product_link}")
                result.append("---")
            
            return "\n".join(result)
        else:
            return f"No products found with the name '{product_name}'."

    except mysql.connector.Error as e:
        return f"Database error: {e}"
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        if 'mydb' in locals() and mydb:
            mydb.close()

# Load FAQ data
faq_data = load_faq('faq.csv')

# Create the FAQ Agent
faq_agent = Agent(
    name="FAQ Agent",
    role="Answer questions based on the provided FAQ data",
    model=Gemini(
        id="gemini-2.0-flash-exp",
        api_key=GEMINI_API_KEY,
        generative_model_kwargs={},
        generation_config={}
    ),
    instructions=f"""You are an FAQ assistant for an e-commerce store. 
    Use the following FAQ data to answer questions: {faq_data}
    If you don't find a direct answer in the FAQ data, provide a helpful response based on general e-commerce knowledge.
    Always be polite and professional.""",
    show_tool_calls=False,  # Hide tool calls
    markdown=True,
)

# Create the Order Status Agent
order_status_agent = Agent(
    name="Order Status Agent",
    role="Retrieve order status based on email or order ID",
    model=Gemini(
        id="gemini-2.0-flash-exp",
        api_key=GEMINI_API_KEY,
        generative_model_kwargs={},
        generation_config={}
    ),
    tools=[get_order_status],
    instructions="""You are an order status assistant. 
    Use the get_order_status tool to retrieve order status information.
    Always ask for either an email address or order ID if the user doesn't provide one.
    Explain what each order status means in customer-friendly language.""",
    show_tool_calls=False,  # Hide tool calls
    markdown=True,
)

# Create the Product Search Agent
product_search_agent = Agent(
    name="Product Search Agent",
    role="Search for products by name",
    model=Gemini(
        id="gemini-2.0-flash-exp",
        api_key=GEMINI_API_KEY,
        generative_model_kwargs={},
        generation_config={}
    ),
    tools=[search_products],
    instructions="""You are a product search assistant.
    Use the search_products tool to find products based on the user's query.
    If the user asks about products or mentions looking for something, help them find it.
    Always ask for clarification if the product name is ambiguous.""",
    show_tool_calls=False,  # Hide tool calls
    markdown=True,
)

# Create the Agent Team
agent_team = Agent(
    team=[faq_agent, order_status_agent, product_search_agent],
    model=Gemini(
        id="gemini-2.0-flash-exp",
        api_key=GEMINI_API_KEY,
        generative_model_kwargs={},
        generation_config={}
    ),
    instructions="""You are an e-commerce assistant for our WooCommerce store.
    
    Your capabilities include:
    1. Answering frequently asked questions about our store, products, shipping, returns, etc.
    2. Checking order status when customers provide their email or order ID
    3. Helping customers find products by searching our product catalog
    
    Delegate tasks to the appropriate sub-agent based on the user's query.
    
    Always be helpful, friendly, and professional. If you're unsure about something, acknowledge that and offer alternative assistance.
    
    Start conversations by introducing yourself as the store's virtual assistant and briefly mentioning what you can help with.
    """,
    show_tool_calls=False,  # Hide tool calls
    markdown=True,
)

# Function to clean agent status messages from the response
def clean_agent_status(text):
    # Remove lines that contain agent status messages
    if not text:
        return text
        
    # Remove "Running: transfer_task_to..." messages
    text = re.sub(r'Running: transfer_task_to_\w+\(.*?\)', '', text)
    
    # Remove other potential agent status messages
    text = re.sub(r'Running: \w+\(.*?\)', '', text)
    
    # Remove empty lines that might be left after removing status messages
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()

# Function to process user queries for Gradio
def process_query(message, history):
    try:
        # Get the response from the agent
        response = agent_team.run(message)
        
        # Extract just the content from the RunResponse object
        if hasattr(response, 'content'):
            # If it's a RunResponse object, get just the content
            response_text = response.content
        else:
            # If it's already a string, use it directly
            response_text = str(response)
        
        # Clean any agent status messages from the response
        response_text = clean_agent_status(response_text)
            
        # Return the user message and bot response as a tuple
        return response_text
    except Exception as e:
        return f"An error occurred: {e}\nPlease try again with a different query."

# Create Gradio interface
def create_gradio_interface():
    # Custom CSS for better appearance
    custom_css = """
    .gradio-container {
        font-family: 'Arial', sans-serif;
    }
    .chat-message {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .user-message {
        background-color: #e6f7ff;
    }
    .bot-message {
        background-color: #f0f0f0;
    }
    """
    
    # Create the Gradio interface
    with gr.Blocks(css=custom_css) as demo:
        gr.Markdown("# WooCommerce Store Assistant")
        gr.Markdown("""
        Welcome to our WooCommerce Store Assistant! I can help you with:
        - Answering frequently asked questions about our store
        - Checking the status of your orders (provide your email or order ID)
        - Finding products in our catalog
        """)
        
        chatbot = gr.Chatbot(
            label="Chat",
            height=500,
            show_copy_button=True
        )
        
        with gr.Row():
            msg = gr.Textbox(
                label="Type your message here",
                placeholder="Ask me anything about our store, products, or your orders...",
                scale=9
            )
            submit = gr.Button("Send", scale=1)
        
        with gr.Row():
            clear = gr.Button("Clear Conversation")
        
        # Example queries to help users get started
        gr.Examples(
            examples=[
                "What's your return policy?",
                "I want to check my order status. My email is customer@example.com",
                "Do you have any t-shirts available?",
                "How long does shipping take?",
                "What payment methods do you accept?"
            ],
            inputs=msg
        )
        
        # Set up event handlers
        def user_input(user_message, history):
            # Add user message to history
            return "", history + [[user_message, None]]
        
        def bot_response(history):
            # Process the last user message
            if history and history[-1][1] is None:
                user_message = history[-1][0]
                bot_message = process_query(user_message, history[:-1])
                history[-1][1] = bot_message
            return history
        
        submit.click(
            user_input, 
            inputs=[msg, chatbot], 
            outputs=[msg, chatbot],
            queue=False
        ).then(
            bot_response,
            inputs=[chatbot],
            outputs=[chatbot]
        )
        
        msg.submit(
            user_input, 
            inputs=[msg, chatbot], 
            outputs=[msg, chatbot],
            queue=False
        ).then(
            bot_response,
            inputs=[chatbot],
            outputs=[chatbot]
        )
        
        clear.click(lambda: None, None, chatbot, queue=False)
        
        # Add a welcome message when the interface loads
        demo.load(lambda: [[None, "Hi there! I'm your WooCommerce store assistant. How can I help you today?"]], None, chatbot)
    
    return demo

def main():
    # Create and launch the Gradio interface
    demo = create_gradio_interface()
    demo.launch(share=True)  # Set share=False in production

if __name__ == "__main__":
    main()