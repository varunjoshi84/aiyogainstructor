# AI Yoga Instructor

A web application powered by GROQ AI and Google Gemini to provide yoga instruction, pose analysis, and chat-based interaction.

## Features

- Chat with an AI yoga assistant
- Upload and analyze yoga poses with visual feedback
- User authentication system
- Chat history tracking for logged-in users

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Flask (Python)
- Database: MongoDB
- AI: GROQ API for chat, Google Gemini for image analysis
- Deployment: Railway

## Deployment Instructions for Railway

### Prerequisites

- A Railway account
- A MongoDB database (MongoDB Atlas recommended)
- GROQ API key
- Google Gemini API key

### Steps to Deploy

1. **Fork or clone this repository**

2. **Create a MongoDB Atlas database**
   - Set up a free tier cluster
   - Create a database user
   - Get your connection string

3. **Set up Railway project**
   - Connect your GitHub repo
   - Railway will automatically detect your `railway.json` configuration

4. **Configure environment variables in Railway dashboard**
   - `MONGODB_URI`: Your MongoDB connection string
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `GROQ_API_KEY`: Your GROQ API key
   - `SECRET_KEY`: A random secure string for session encryption

5. **Deploy the application**
   - Railway will automatically build and deploy your app
   - Access your app at the provided Railway URL

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up a `.env` file with the required environment variables
4. Run the application: `python app.py`

## Environment Variables

- `MONGODB_URI`: MongoDB connection string
- `GEMINI_API_KEY`: Google Gemini API key
- `GROQ_API_KEY`: GROQ API key
- `SECRET_KEY`: Secret key for Flask session

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Thanks to GROQ for providing the AI capabilities
