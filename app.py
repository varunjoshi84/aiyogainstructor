import os
import requests
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from flask import g
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for PythonAnywhere free tier
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables")

# Configure Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in environment variables")

# Initialize Gemini model only if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# MongoDB Configuration
# Try to use the MongoDB URI from environment variables, fallback to local MongoDB
MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI or "your-actual-username" in MONGODB_URI:
    # Fallback to local MongoDB if URI is not set or contains placeholder
    MONGODB_URI = "mongodb://localhost:27017/yoga_db"
    print(f"Using local MongoDB: {MONGODB_URI}")
else:
    print(f"Using MongoDB URI from environment: {MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else MONGODB_URI}")

# Check if we're in different environments
is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None
is_pythonanywhere = os.environ.get('PYTHONANYWHERE') is not None

def get_db():
    if 'db' not in g:
        try:
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            g.client = client
            g.db = client.get_database()
            # Test connection
            g.client.server_info()
        except Exception as err:
            print(f"Database connection error: {err}")
            # Return None for demo mode
            if is_railway:
                print("Running in demo mode on Railway without database")
                return None
            raise
    return g.db

def init_db():
    try:
        db = get_db()
        if db is None:
            print("Skipping database initialization - running in demo mode")
            return
            
        # Create users collection if it doesn't exist
        if "users" not in db.list_collection_names():
            db.create_collection("users")
            print("Created users collection")
            
        # Create chat_history collection if it doesn't exist
        if "chat_history" not in db.list_collection_names():
            db.create_collection("chat_history")
            print("Created chat_history collection")
            
    except Exception as e:
        print(f"Database initialization error: {e}")
        if is_railway:
            print("Continuing in demo mode without database")

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'client'):
        g.client.close()

def validate_api_keys():
    """Validate API keys and print status message"""
    print("\n=== API Configuration Status ===")
    
    # Check MongoDB connection
    try:
        db = get_db()
        if db is None:
            print("MongoDB Connection: Skipped - running in demo mode")
        else:
            db_info = db.command("serverStatus")
            print(f"MongoDB Connection: Successful (Version: {db_info.get('version', 'Unknown')})")
    except Exception as e:
        print(f"MongoDB Connection: Failed - {str(e)}")
    
    # Check environment
    if is_railway:
        print("Environment: Railway")
    elif is_pythonanywhere:
        print("Environment: PythonAnywhere")
    else:
        print("Environment: Local/Other")
    
    # Check Gemini API
    if GEMINI_API_KEY:
        if GEMINI_API_KEY == "your_gemini_api_key_here":
            print("Gemini API: Not configured (placeholder key)")
        else:
            print("Gemini API: Key configured")
    else:
        print("Gemini API: Missing key")
    
    # Check Groq API
    if GROQ_API_KEY:
        if GROQ_API_KEY == "your_groq_api_key_here":
            print("Groq API: Not configured (placeholder key)")
        else:
            print("Groq API: Key configured")
    else:
        print("Groq API: Missing key")
    
    print("=============================\n")

# Initialize database on startup
with app.app_context():
    init_db()
    validate_api_keys()

# Fetch banned words from external source
BANNED_WORDS_URL = "http://www.bannedwordlist.com/lists/swearWords.txt"

def fetch_banned_words():
    """Fetch banned words from the external source."""
    try:
        response = requests.get(BANNED_WORDS_URL)
        if response.status_code == 200:
            return set(response.text.splitlines())  # Store as a set for fast lookup
    except Exception as e:
        print("Error fetching banned words:", str(e))
    return set()

# Load banned words on startup
BANNED_WORDS = fetch_banned_words()

def is_message_inappropriate(user_input):
    """Check if user input contains banned words."""
    words = user_input.lower().split()
    return any(word in BANNED_WORDS for word in words)

def ask_groq(user_input):
    """Send a query to Groq API with conversation history."""
    if not GROQ_API_KEY:
        return "Error: Groq API key is missing."
    
    # Import required modules at the function level
    import urllib3
    import requests
    from requests.exceptions import SSLError, RequestException
    
    # Suppress SSL warnings for development environment
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ✅ Check for inappropriate content
    if is_message_inappropriate(user_input):
        return "Please keep the conversation respectful."

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # ✅ Retrieve chat history from session
    if "chat_history" not in session:
        session["chat_history"] = []

    # Append user message to chat history
    session["chat_history"].append({"role": "user", "content": user_input})

    # ✅ Keep only the last 5 messages for context
    session["chat_history"] = session["chat_history"][-5:]

    data = {
        "model": "llama3-8b-8192",  # ✅ Supported Groq model
        "messages": [{"role": "system", "content": "You are a knowledgeable AI yoga instructor. you have to only give response to yoga related question"}] + session["chat_history"],
        "temperature": 0.7,
        "max_tokens": 100
    }

    try:
        # Make the API request with SSL verification disabled
        response = requests.post(url, headers=headers, json=data, verify=False)
        response.raise_for_status()  # Raise an exception for bad status codes
        response_json = response.json()

        if "choices" in response_json:
            ai_response = response_json["choices"][0]["message"]["content"].strip()
            session["chat_history"].append({"role": "assistant", "content": ai_response})  # ✅ Store AI response
            
            # Save chat to database if user is logged in
            if session.get('logged_in') and session.get('user_id'):
                try:
                    db = get_db()
                    if db:
                        db.chat_history.insert_one({
                            "user_id": session['user_id'],
                            "message": user_input,
                            "response": ai_response,
                            "created_at": datetime.now()
                        })
                except Exception as e:
                    print(f"Error saving chat history: {str(e)}")
                
            return ai_response
        else:
            return "Error: Unexpected API response."

    except SSLError as e:
        return "Error: SSL certificate verification failed. This is expected in development environment and won't affect functionality."
    except RequestException as e:
        return f"Error: Failed to connect to Groq API - {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error occurred - {str(e)}"

def analyze_pose(image_data):
    """Analyze yoga pose using Gemini API."""
    try:
        # Convert image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare the prompt for Gemini
        prompt = """Analyze this yoga pose and provide:
        1. The name of the pose
        2. Key alignment points
        3. Common mistakes to avoid
        4. Benefits of the pose
        5. Modifications for beginners
        
        Format the response in a clear, structured way."""
        
        # Create the image part for Gemini
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": image_base64
            }
        ]
        
        # Generate response
        response = model.generate_content([prompt, image_parts[0]], stream=False)
        
        if response and response.text:
            # Extract pose name from the response
            pose_name = "Yoga Pose"  # Default name
            if "1." in response.text:
                pose_name = response.text.split("1.")[0].strip()
            
            return {
                "success": True,
                "analysis": response.text,
                "pose_name": pose_name,
                "feedback": "Here's your pose analysis:"
            }
        else:
            return {
                "success": False,
                "error": "Could not analyze the pose. Please try again."
            }
            
    except Exception as e:
        print(f"Error in pose analysis: {str(e)}")
        return {
            "success": False,
            "error": f"An error occurred while analyzing the pose: {str(e)}"
        }

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect('/app')
    return render_template('landing.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if username already exists
        existing_user = db.users.find_one({"username": username})
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Hash password and create new user
        hashed_password = generate_password_hash(password)
        user_id = db.users.insert_one({
            "username": username,
            "password": hashed_password,
            "created_at": datetime.now()
        }).inserted_id
        
        # Set session variables
        session['user_id'] = str(user_id)
        session['username'] = username
        session['logged_in'] = True
        
        return jsonify({
            'message': 'Registration successful',
            'redirect': '/app'
        }), 201
    except Exception as err:
        return jsonify({'error': str(err)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    print(f"Login attempt for username: {username}")
    
    if not username or not password:
        print("Error: Username and password are required")
        return jsonify({'error': 'Username and password are required'}), 400
    
    try:
        print("Attempting to get database connection...")
        db = get_db()
        if db is None:
            print("Error: Database connection returned None")
            return jsonify({'error': 'Database not available'}), 500
        
        # Get user from database
        print(f"Looking up user: {username}")
        user = db.users.find_one({"username": username})
        
        if user:
            print("User found, checking password")
            # Debug info about the user document
            print(f"User document: {str(type(user))}, ID: {str(type(user.get('_id')))}")
            
            if check_password_hash(user['password'], password):
                print("Password matched, setting up session")
                user_id = str(user['_id'])
                print(f"User ID for session: {user_id}")
                
                session['user_id'] = user_id
                session['username'] = username
                session['logged_in'] = True
                
                print("Login successful")
                return jsonify({
                    'message': 'Login successful',
                    'redirect': '/app'
                }), 200
            else:
                print("Password check failed")
                return jsonify({'error': 'Invalid username or password'}), 401
        else:
            print(f"No user found with username: {username}")
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as err:
        print(f"LOGIN ERROR: {str(err)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(err)}), 500

@app.route('/skip-login')
def skip_login():
    """Handle guest access."""
    session['guest'] = True
    session.pop('logged_in', None)  # Remove login status if present
    return '', 200  # Return empty response with 200 status code

@app.route('/logout')
def logout():
    """Handle logout functionality."""
    session.clear()
    return redirect('/')

@app.route('/app')
def app_route():
    if 'logged_in' not in session and 'guest' not in session:
        return redirect('/')
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chatbot requests."""
    if not (session.get('logged_in') or session.get('guest')):
        return jsonify({"error": "Please log in or continue as guest"}), 401
    
    data = request.json
    user_message = data.get("message", "")
    
    if not user_message.strip():
        return jsonify({"error": "Please ask a valid question"}), 400

    try:
        ai_response = ask_groq(user_message)
        return jsonify({"response": ai_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pose', methods=['POST'])
def pose_correction():
    """Handle pose correction requests."""
    if not session.get('logged_in'):
        return jsonify({"error": "Please log in to use the pose analysis feature"}), 401
        
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    try:
        # Read the image file
        image_data = file.read()
        
        # Check if the file is an image
        if not file.content_type.startswith('image/'):
            return jsonify({
                "success": False,
                "error": "Please upload an image file"
            })
            
        # Analyze the pose
        result = analyze_pose(image_data)
        
        if result['success']:
            return jsonify({
                "success": True,
                "feedback": result['analysis'],
                "pose_name": result['pose_name']
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            })
            
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"An error occurred while processing the image: {str(e)}"
        })

@app.route('/new-chat', methods=['POST'])
def new_chat():
    """Clear the chat history."""
    if 'chat_history' in session:
        session.pop('chat_history')
    return jsonify({'status': 'success'})

# New routes for chat history
@app.route('/get-chat-history', methods=['GET'])
def get_chat_history():
    """Get user's chat history from MongoDB."""
    if not session.get('logged_in'):
        return jsonify({"error": "Please log in to view chat history"}), 401
    
    try:
        db = get_db()
        if db is None:
            return jsonify({"error": "Database not available"}), 500
        
        # Get chat history sorted by creation date
        user_id = session['user_id']
        chats = list(db.chat_history.find(
            {"user_id": user_id},
            {"_id": 1, "message": 1, "response": 1, "created_at": 1}
        ).sort("created_at", -1).limit(50))  # Get most recent 50
        
        # Convert ObjectId to string for JSON serialization
        for chat in chats:
            chat['_id'] = str(chat['_id'])
            # Convert datetime to ISO format string
            if isinstance(chat.get('created_at'), datetime):
                chat['created_at'] = chat['created_at'].isoformat()
        
        return jsonify({"history": chats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Check which environment we're running in
    if is_pythonanywhere:
        # In PythonAnywhere, this block won't run as the WSGI script imports the app
        print("Running on PythonAnywhere")
    elif is_railway:
        # On Railway, the PORT environment variable will be set
        port = int(os.environ.get('PORT', 5000))
        debug = False
        app.run(host='0.0.0.0', port=port, debug=debug)
    else:
        # Local development
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=True)