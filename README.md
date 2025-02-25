# FAQ Bot

This project contains several FAQ bots.

## Setup

1.  Create a Python environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3.  Create a `.env` file with the following variables:

    ```
    GEMINI_API_KEY=your_gemini_api_key
    DB_NAME=your_db_name
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_HOST=your_db_host
    DB_PORT=your_db_port
    WC_URL=your_wc_url
    WC_KEY=your_wc_key
    WC_SECRET=your_wc_secret
    ```

4.  Run the bots:

    ```bash
    python advanced_faq_bot.py
    python ecommerce_faq_bot.py
    python product_search_bot.py
