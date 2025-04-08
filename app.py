import os
import requests
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import urlparse
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Production security headers
from flask_talisman import Talisman
Talisman(
    app,
    content_security_policy={
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:"]
    }
)

# Initialize Gemini model with the newer version
model = genai.GenerativeModel('gemini-1.5-flash')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/yoga_db')

# Fix Render's DATABASE_URL if needed
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    DATABASE_URL += '?sslmode=require'

def get_db():
    if 'db' not in g:
        g.db = create_engine(DATABASE_URL)
    return g.db

def init_db():
    db = get_db()
    
    # Create users table
    db.execute(text('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''))
    
    # Create chat_history table
    db.execute(text('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    '''))
    
    # No need to commit with SQLAlchemy execute

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        # SQLAlchemy engine doesn't need explicit closing
        pass

# Initialize database on startup
with app.app_context():
    init_db()

# ✅ Load Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ✅ Fetch banned words from external source
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

# ✅ Load banned words on startup
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

    # ✅ Append user message to chat history
    session["chat_history"].append({"role": "user", "content": user_input})

    # ✅ Keep only the last 5 messages for context
    session["chat_history"] = session["chat_history"][-5:]

    data = {
        "model": "llama3-8b-8192",  # ✅ Supported Groq model
        "messages": [{"role": "system", "content": "You are a knowledgeable AI yoga instructor."}] + session["chat_history"],
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        # Make the API request with SSL verification disabled
        response = requests.post(url, headers=headers, json=data, verify=False)
        response.raise_for_status()  # Raise an exception for bad status codes
        response_json = response.json()

        if "choices" in response_json:
            ai_response = response_json["choices"][0]["message"]["content"].strip()
            session["chat_history"].append({"role": "assistant", "content": ai_response})  # ✅ Store AI response
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
        
        # Check if username already exists
        result = db.execute(text('SELECT id FROM users WHERE username = :username'),
                          {'username': username}).fetchone()
        if result:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Hash password and create new user
        hashed_password = generate_password_hash(password)
        result = db.execute(
            text('INSERT INTO users (username, password) VALUES (:username, :password) RETURNING id'),
            {'username': username, 'password': hashed_password}
        ).fetchone()
        
        user_id = result[0]
        
        # Set session variables
        session['user_id'] = user_id
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
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    try:
        db = get_db()
        
        # Get user from database
        result = db.execute(
            text('SELECT id, password FROM users WHERE username = :username'),
            {'username': username}
        ).fetchone()
        
        if result and check_password_hash(result[1], password):
            session['user_id'] = result[0]
            session['username'] = username
            session['logged_in'] = True
            return jsonify({
                'message': 'Login successful',
                'redirect': '/app'
            }), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as err:
        return jsonify({'error': str(err)}), 500

@app.route('/save_chat', methods=['POST'])
def save_chat():
    if not session.get('logged_in'):
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    message = data.get('message')
    response = data.get('response')
    user_id = session.get('user_id')
    
    try:
        db = get_db()
        
        db.execute(
            text('INSERT INTO chat_history (user_id, message, response) VALUES (:user_id, :message, :response)'),
            {'user_id': user_id, 'message': message, 'response': response}
        )
        
        return jsonify({'success': True}), 200
    except Exception as err:
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

if __name__ == '__main__':
    # Prevent running dev server in production
    if os.getenv('FLASK_ENV') != 'production':
        app.run(host='127.0.0.1', port=5001, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')