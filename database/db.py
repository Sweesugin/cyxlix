import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "cyxlix_db"

if not MONGO_URI:
    raise Exception("MONGO_URI not found in .env file")

try:
    # Connect to MongoDB with 5 seconds timeout
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Ping database to verify connection
    client.admin.command('ping')
    db = client[DB_NAME]
    print("MongoDB Atlas connected successfully")
except Exception as e:
    print(f"MongoDB Atlas connection failed: {e}")
    raise e

def get_db():
    """Returns the database client instance."""
    return db
