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

    # Construct the SQL query to retrieve the latest 10 orders
    query = """
    SELECT
        ID as order_id,
        post_status as order_status
    FROM
        wp_posts
    WHERE
        post_type = 'shop_order'
    ORDER BY
        ID DESC
    LIMIT 10;
    """

    mycursor.execute(query)

    myresult = mycursor.fetchall()

    if myresult:
        print("Latest 10 Orders:")
        for row in myresult:
            order_id = row[0]
            order_status = row[1]
            print(f"Order ID: {order_id}, Status: {order_status}")
    else:
        print("No orders found.")

except mysql.connector.Error as e:
    print(f"Error connecting to MySQL database: {e}")
