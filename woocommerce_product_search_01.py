import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
WC_URL = os.getenv("WC_URL")

try:
    mydb = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    print("MySQL database connection successful")

    mycursor = mydb.cursor()

    product_name = input("Enter the product name: ")

    # Construct the SQL query to retrieve the product ID, title, and price
    query = f"""
    SELECT
        p.ID,
        p.post_title,
        pm.meta_value AS price
    FROM
        wp_posts p
    LEFT JOIN wp_postmeta pm ON p.ID = pm.post_id
    WHERE
        p.post_type = 'product'
        AND p.post_status = 'publish'
        AND p.post_title LIKE '%{product_name}%'
        AND pm.meta_key = '_price'
    LIMIT 10;
    """

    mycursor.execute(query)

    myresult = mycursor.fetchall()

    if myresult:
        print("Product Search Results:")
        for row in myresult:
            product_id = row[0]
            product_title = row[1]
            product_price = row[2] if row[2] else "N/A"
            product_link = f"{WC_URL}/product/{product_title.lower().replace(' ', '-')}"
            print(f"Title: {product_title}, Price: ₹{product_price}, Link: {product_link}")
    else:
        print(f"No products found with the name {product_name}.")

except mysql.connector.Error as e:
    print(f"Error connecting to MySQL database: {e}")
