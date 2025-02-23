from agno.agent import Agent
from agno.models.google.gemini import Gemini
import os
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth  # Added missing import

load_dotenv()

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Check if all required environment variables are set
if not GEMINI_API_KEY:
    raise ValueError("Missing required environment variables")

wc_url = "https://wholesale.silkroademart.com"
wc_key = "ck_7f762d0bb0a2243c237d76fc21c1c4210b3c9453"
wc_secret = "cs_70dda921540d202bcdd980ddbeb8c7adb3f8d518"

def woocommerce_tool(order_id: str) -> str:
    """Tool to interact with the WooCommerce API"""
    try:
        auth = (wc_key, wc_secret)
        response = requests.get(
            f"{wc_url}/wp-json/wc/v3/orders/{order_id}", 
            auth=HTTPBasicAuth(*auth)
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        customer_name = f"{data['billing']['first_name']} {data['billing']['last_name']}"
        total = data['total']
        status = data.get('status', 'unknown')  # Handle missing status
        return f"Order {order_id} for {customer_name} with total {total} is currently {status}"
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

woocommerce_tool.__name__ = "WooCommerceTool"
woocommerce_tool.description = "Interact with the WooCommerce API to get order status"
woocommerce_tool.parameters = {
    "order_id": {"type": "string", "description": "The ID of the order to retrieve"}
}

# Create the WooCommerce Agent
agent = Agent(
    model=Gemini(
        id="gemini-2.0-flash-exp", 
        api_key=GEMINI_API_KEY, 
        generative_model_kwargs={}, 
        generation_config={}
    ),
    tools=[woocommerce_tool],
    instructions="Interact with the WooCommerce API to get order status. Use the woocommerce_tool and provide the order ID.",
    show_tool_calls=True,
    markdown=True,
)

def display_menu():
    """Display the main menu options"""
    print("\n=== Agent Selection Menu ===")
    print("1. Run WooCommerce Agent")
    print("2. Exit")
    return input("Enter your choice (1-2): ")

def run_woocommerce_agent(agent):
    """Run the WooCommerce Agent"""
    print("\nExecuting WooCommerce Agent...")
    order_id = input("\nEnter the order ID to retrieve: ")
    woocommerce_response = woocommerce_tool(order_id)
    print(f"WooCommerce Agent Response: {woocommerce_response}")
    return woocommerce_response

def main():
    while True:
        choice = display_menu()
        
        if choice == '1':
            run_woocommerce_agent(agent)
        elif choice == '2':
            print("\nExiting program...")
            break
        else:
            print("\nInvalid choice. Please select a number between 1 and 2.")

if __name__ == "__main__":
    main()