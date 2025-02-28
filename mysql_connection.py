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

    # You can perform database operations here
    # Example:
    # mycursor = mydb.cursor()
    # mycursor.execute("SELECT * FROM your_table")
    # myresult = mycursor.fetchall()
    # for x in myresult:
    #   print(x)

except mysql.connector.Error as e:
    print(f"Error connecting to MySQL database: {e}")
