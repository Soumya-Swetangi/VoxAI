from flask import Flask, jsonify, Response, send_from_directory
from flask_cors import CORS
import praw
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import csv
import io
from datetime import datetime, timezone
import logging
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for Codespaces

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID", "3WyjMcNGIxxcZ72g6qBzrg"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET", "BdtzJ07zEIYYASpn_dRUEspBoWXJRg"),
    user_agent="public-opinion-tracker/1.0"
)

# News API key
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "5653e38eed5d456abb58838de30cafcb")

# Initialize sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Store sentiments globally
sentiments = {'reddit': [], 'news': []}

def fetch_reddit_posts(topic):
    try:
        subreddit = reddit.subreddit('all').search(topic, limit=5)
        posts = []
        for submission in subreddit:
            score = analyzer.polarity_scores(submission.title)
            posts.append({
                'text': submission.title,
                'compound': score['compound'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'reddit'
            })
        return posts
    except Exception as e:
        logging.error(f"Reddit fetch error: {str(e)}")
        return []

def fetch_news_articles(topic):
    try:
        url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={NEWS_API_KEY}&language=en&sortBy=publishedAt&pageSize=5"
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get('articles', [])
        news = []
        for article in articles:
            title = article.get('title', '')
            if title:
                score = analyzer.polarity_scores(title)
                news.append({
                    'text': title,
                    'compound': score['compound'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'news'
                })
        return news
    except Exception as e:
        logging.error(f"News fetch error: {str(e)}")
        return []

@app.route('/')
def index():
    try:
        logging.debug("Serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logging.error(f"Error serving index.html: {str(e)}")
        return jsonify({'error': 'Failed to serve index.html'}), 500

@app.route('/api/debug')
def debug():
    return jsonify({'message': 'Server is running updated app.py', 'routes': ['/', '/api/analyze/<topic>', '/api/insights/<topic>', '/api/data', '/api/export/csv']})

@app.route('/api/analyze/<topic>')
def analyze_topic(topic):
    try:
        reddit_posts = fetch_reddit_posts(topic)
        news_articles = fetch_news_articles(topic)
        sentiments['reddit'] = reddit_posts
        sentiments['news'] = news_articles
        logging.debug(f"Analyzed topic: {topic}, Reddit: {len(reddit_posts)}, News: {len(news_articles)}")
        return jsonify({'reddit': reddit_posts, 'news': news_articles})
    except Exception as e:
        logging.error(f"Analyze error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/<topic>')
def get_insights(topic):
    try:
        summary = f"Public sentiment on {topic} shows mixed opinions."
        themes = ['Innovation', 'Ethics', 'Impact']
        recommendations = ['AI Governance', 'Tech Trends']
        return jsonify({
            'summary': summary,
            'themes': themes,
            'recommendations': recommendations
        })
    except Exception as e:
        logging.error(f"Insights error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data')
def get_data():
    try:
        logging.debug(f"Sentiments data: {sentiments}")
        return jsonify(sentiments)
    except Exception as e:
        logging.error(f"Data error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv')
def export_csv():
    try:
        flat_data = (
            [{'text': s['text'], 'compound': s['compound'], 'timestamp': s['timestamp'], 'source': s['source']} for s in sentiments.get('reddit', [])] +
            [{'text': s['text'], 'compound': s['compound'], 'timestamp': s['timestamp'], 'source': s['source']} for s in sentiments.get('news', [])]
        )

        if not flat_data:
            logging.warning("No data available for CSV export")
            return jsonify({'error': 'No data available to export'}), 400

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['text', 'compound', 'timestamp', 'source'])
        writer.writeheader()
        writer.writerows(flat_data)
        csv_content = '\ufeff' + output.getvalue()  # Add UTF-8 BOM for Excel
        output.close()

        logging.info("CSV generated successfully")
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=sentiments.csv'}
        )
    except Exception as e:
        logging.error(f"CSV export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port= 5000, debug=True)