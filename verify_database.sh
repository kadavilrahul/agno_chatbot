#!/bin/bash

# Debugging script for PostgreSQL and pgvector setup

# Ensure we're using the postgres user
echo "Running as user: $(whoami)"

# Check PostgreSQL installation
echo "PostgreSQL Version:"
psql --version

# List all databases
echo -e "\nAvailable Databases:"
sudo -u postgres psql -l

# Check for pgvector extension
echo -e "\nVector Extension Check:"
sudo -u postgres psql -c "\dx vector"

# Check database tables
echo -e "\nTables in faq_db:"
sudo -u postgres psql -d faq_db -c "\dt"

# Detailed database information
echo -e "\nDatabase Details:"
sudo -u postgres psql -d faq_db << EOF
\dn  -- List schemas
\dx  -- List extensions
\du  -- List roles
EOF

# Python connection test
echo -e "\nPython Connection Test:"
sudo -u postgres python3 << END
import os
import sys
import psycopg2

# Print Python and library versions
print("Python version:", sys.version)
print("psycopg2 version:", psycopg2.__version__)

try:
    # Read environment variables
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('DB_'):
                print(line.strip())

    # Attempt database connection
    conn = psycopg2.connect(
        dbname="faq_db",
        user="faq_user",
        password="faq_2@",
        host="localhost",
        port="5432"
    )
    
    print("\nDatabase Connection: Successful")
    
    # Check vector extension
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("SELECT '[1,2,3]'::vector")
        print("Vector Extension: Working")
    
    conn.close()
except Exception as e:
    print(f"Connection Error: {e}")
END

echo -e "\nVerification script completed."