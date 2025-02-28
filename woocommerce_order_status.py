import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

try:
    mydb = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    print("MySQL database connection successful")

    mycursor = mydb.cursor()

    email = input("Enter the email ID (or leave blank): ")
    order_id = input("Enter the order ID (or leave blank): ")

    # Construct the SQL query to retrieve the order status
    query = f"""
    SELECT
        p.ID as order_id,
        p.post_status as order_status
    FROM
        wp_posts p
        LEFT JOIN wp_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_billing_email'
    WHERE
        p.post_type = 'shop_order'
        AND (p.ID = '{order_id}' OR pm.meta_value = '{email}')
    """

    mycursor.execute(query)

    myresult = mycursor.fetchall()

    if myresult:
        for row in myresult:
            order_id = row[0]
            order_status = row[1]
            print(f"Order ID: {order_id}, Status: {order_status}")
    else:
        print(f"Order with ID {order_id} not found.")

except mysql.connector.Error as e:
    print(f"Error connecting to MySQL database: {e}")
