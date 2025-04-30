# VoxAI
Public Opinion Tracker
Overview
The Public Opinion Tracker is a web-based application that analyzes public sentiment on user-specified topics by aggregating and evaluating data from Reddit posts and news articles. Using sentiment analysis, it visualizes public opinion through interactive bar charts and provides real-time insights into social media and news sentiment trends. The application is built with Flask for the backend, Tailwind CSS and Chart.js for the frontend, and integrates APIs for data collection.
Features

Sentiment Analysis: Analyzes sentiment of Reddit post titles and news article headlines using the VADER sentiment analyzer.
Data Sources:
Reddit: Fetches up to 10 recent posts from the "all" subreddit for a given topic.
News: Retrieves up to 10 recent articles via the News API.


Visualization: Displays sentiment scores (-1 to 1) in bar charts for Reddit and news data.
Real-Time Updates: Stores and displays recent analyses in a JSON file, with timestamps for tracking.
User Interface: Simple, responsive UI with topic input and animated visualizations.
Data Persistence: Saves sentiment data to a local data.json file for historical reference.

Technologies Used

Backend: Python, Flask, Flask-CORS
Frontend: HTML, Tailwind CSS, Chart.js
APIs: Reddit (PRAW), News API
Sentiment Analysis: VADER Sentiment
Data Storage: JSON file

Installation
Prerequisites

Python 3.8+
Git
Reddit API credentials (Client ID, Client Secret)
News API key

Steps

Clone the Repository:
git clone https://github.com/your-username/public-opinion-tracker.git
cd public-opinion-tracker


Install Dependencies:Create a virtual environment and install required packages:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install flask flask-cors praw requests vaderSentiment


Configure API Keys:Update the API credentials in app.py:

Replace client_id and client_secret with your Reddit API credentials.
Replace NEWS_API_KEY with your News API key.Alternatively, use a .env file with python-dotenv for secure configuration (see Enhancements below).


Run the Application:Start the Flask server:
python app.py

Access the application at http://localhost:5000.


Usage

Open the web interface in a browser.
Enter a topic (e.g., "AI", "Climate Change") in the input field and click "Analyze".
View sentiment analysis results in two bar charts:
Reddit Sentiment: Sentiment scores for up to 10 Reddit post titles.
News Sentiment: Sentiment scores for up to 10 news article headlines.


Scroll to the "Recent Analyses" section to see the latest sentiment data with timestamps.
Sentiment scores range from -1 (negative) to 1 (positive), with 0 indicating neutral sentiment.

File Structure
public-opinion-tracker/
├── app.py              # Flask backend with API routes
├── index.html          # Frontend HTML with Tailwind CSS and Chart.js
├── data.json           # Stores sentiment analysis data
├── README.md           # Project documentation
└── requirements.txt    # Python dependencies

API Endpoints

GET /: Serves the main web interface (index.html).
GET /api/analyze/<topic>: Analyzes sentiment for the given topic and returns Reddit and news sentiment data, including average scores.
GET /api/data: Retrieves all stored sentiment data from data.json.

Enhancements (Planned)

Secure API Keys: Use a .env file to store sensitive API credentials.
Advanced Visualizations: Add pie charts or word clouds to summarize sentiment distribution.
Data Filtering: Allow users to filter recent analyses by date or source.
Error Handling: Improve user feedback for API errors or invalid inputs.
Database Support: Replace JSON file with SQLite or MongoDB for scalable data storage.
Sentiment Breakdown: Provide detailed sentiment scores (positive, negative, neutral) in addition to compound scores.



Fork the repository.
Create a new branch (git checkout -b feature/your-feature).
Commit your changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a pull request.


Acknowledgments

PRAW for Reddit API integration.
News API for news article data.
VADER Sentiment for sentiment analysis.
Chart.js for data visualization.
Tailwind CSS for responsive styling.

