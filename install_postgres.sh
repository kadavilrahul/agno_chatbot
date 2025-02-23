#!/bin/bash

# Update package list
apt update

# Install PostgreSQL and required packages
apt install -y postgresql postgresql-contrib postgresql-client-common postgresql-client

# Install build dependencies for pgvector
apt install -y build-essential git postgresql-server-dev-all

# Clone and install pgvector
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Start PostgreSQL service
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE faq_db;
CREATE USER faquser WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE faq_db TO faquser;
\c faq_db
CREATE EXTENSION IF NOT EXISTS vector;
EOF

echo "PostgreSQL installation and setup completed!"