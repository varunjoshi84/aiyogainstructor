import os
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime
import sys

# Load environment variables
load_dotenv()

# Test user credentials
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test123"

def create_test_user():
    """Create a test user in the local MongoDB database"""
    print("Creating test user account...")
    
    try:
        # Connect to MongoDB (use local instance)
        client = MongoClient("mongodb://localhost:27017/yoga_db", serverSelectionTimeoutMS=5000)
        db = client.get_database()
        
        # Check if user already exists
        existing_user = db.users.find_one({"username": TEST_USERNAME})
        if existing_user:
            print(f"Test user '{TEST_USERNAME}' already exists!")
            print(f"User ID: {existing_user['_id']}")
            return
            
        # Create new test user
        hashed_password = generate_password_hash(TEST_PASSWORD)
        user_id = db.users.insert_one({
            "username": TEST_USERNAME,
            "password": hashed_password,
            "created_at": datetime.now()
        }).inserted_id
        
        print(f"✅ Test user created successfully!")
        print(f"Username: {TEST_USERNAME}")
        print(f"Password: {TEST_PASSWORD}")
        print(f"User ID: {user_id}")
        
    except Exception as e:
        print(f"❌ Error creating test user: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    create_test_user()