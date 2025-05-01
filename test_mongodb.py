import os
from dotenv import load_dotenv
from pymongo import MongoClient
import sys

# Load environment variables
load_dotenv()

def test_mongodb_connection(use_local=False):
    """Test the MongoDB connection and display database information"""
    print("Testing MongoDB Connection...")
    
    # Get MongoDB URI from environment or use local connection
    if use_local:
        mongodb_uri = "mongodb://localhost:27017/yoga_db"
        print("Using local MongoDB instance for testing")
    else:
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            print("Error: MONGODB_URI not found in environment variables")
            print("Falling back to local MongoDB...")
            mongodb_uri = "mongodb://localhost:27017/yoga_db"
    
    try:
        # Connect to MongoDB
        print(f"Connecting to: {mongodb_uri.split('@')[-1] if '@' in mongodb_uri else mongodb_uri}")
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Check connection by requesting server info
        server_info = client.server_info()
        print(f"✅ Successfully connected to MongoDB!")
        print(f"MongoDB version: {server_info.get('version')}")
        
        # Get database
        db = client.get_database()
        print(f"Database name: {db.name}")
        
        # List collections
        collections = db.list_collection_names()
        if collections:
            print(f"Collections in database: {', '.join(collections)}")
        else:
            print("No collections found in database. Creating test collections...")
            # Create collections if they don't exist
            db.create_collection("users")
            db.create_collection("chat_history")
            print("Created 'users' and 'chat_history' collections")
        
        # Test inserting a document
        test_result = db.test_collection.insert_one({"test": "document", "timestamp": __import__('datetime').datetime.now()})
        print(f"Test document inserted with ID: {test_result.inserted_id}")
        
        # Clean up test document
        db.test_collection.delete_one({"_id": test_result.inserted_id})
        print("Test document deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {str(e)}")
        if not use_local and "local" not in mongodb_uri:
            print("Trying local MongoDB instance instead...")
            return test_mongodb_connection(use_local=True)
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    test_mongodb_connection()