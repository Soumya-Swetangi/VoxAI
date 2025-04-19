from flask import Flask, jsonify, render_template
from flask_cors import CORS
import praw
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json
import os
from datetime import datetime

app = Flask(__name__, template_folder='.')
CORS(app)

# Initialize APIs and sentiment analyzer
reddit = praw.Reddit(
    client_id="3WyjMcNGIxxcZ72g6qBzrg",
    client_secret="BdtzJ07zEIYYASpn_dRUEspBoWXJRg",
    user_agent="public-opinion-tracker/1.0"
)
NEWS_API_KEY = "5653e38eed5d456abb58838de30cafcb"
analyzer = SentimentIntensityAnalyzer()

DATA_FILE = "data.json"

# Initialize data.json if it doesn't exist
# Initialize data.json if it doesn't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({"reddit": [], "news": []}, f)

def get_reddit_sentiment(topic):
    try:
        posts = reddit.subreddit("all").search(topic, limit=10)
        sentiments = []
        for post in posts:
            sentiment = analyzer.polarity_scores(post.title)
            sentiments.append({
                "text": post.title,
                "compound": sentiment['compound'],
                "positive": sentiment['pos'],
                "negative": sentiment['neg'],
                "neutral": sentiment['neu'],
                "timestamp": datetime.utcnow().isoformat()
            })
        return sentiments
    except Exception as e:
        print(f"Reddit error: {e}")
        return []

def get_news_sentiment(topic):
    try:
        url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={NEWS_API_KEY}&pageSize=10"
        response = requests.get(url)
        articles = response.json().get('articles', [])
        sentiments = []
        for article in articles:
            title = article.get('title', '')
            if title:
                sentiment = analyzer.polarity_scores(title)
                sentiments.append({
                    "text": title,
                    "compound": sentiment['compound'],
                    "positive": sentiment['pos'],
                    "negative": sentiment['neg'],
                    "neutral": sentiment['neu'],
                    "timestamp": datetime.utcnow().isoformat()
                })
        return sentiments
    except Exception as e:
        print(f"News API error: {e}")
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze/<topic>')
def analyze_topic(topic):
    reddit_sentiments = get_reddit_sentiment(topic)
    news_sentiments = get_news_sentiment(topic)

    if not reddit_sentiments and not news_sentiments:
        return jsonify({"error": "No data found for this topic"}), 

    # Load existing data
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    # Append new data
    data['reddit'].extend(reddit_sentiments)
    data['news'].extend(news_sentiments)

    # Save updated data
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    # Calculate averages and statistics
    reddit_avg = sum(s['compound'] for s in reddit_sentiments) / len(reddit_sentiments) if reddit_sentiments else 0
    news_avg = sum(s['compound'] for s in news_sentiments) / len(news_sentiments) if news_sentiments else 0
    reddit_stats = {
        "count": len(reddit_sentiments),
        "positive": len([s for s in reddit_sentiments if s['compound'] > 0.05]),
        "negative": len([s for s in reddit_sentiments if s['compound'] < -0.05]),
        "neutral": len([s for s in reddit_sentiments if -0.05 <= s['compound'] <= 0.05])
    }
    news_stats = {
        "count": len(news_sentiments),
        "positive": len([s for s in news_sentiments if s['compound'] > 0.05]),
        "negative": len([s for s in news_sentiments if s['compound'] < -0.05]),
        "neutral": len([s for s in news_sentiments if -0.05 <= s['compound'] <= 0.05])
    }

    return jsonify({
        "reddit": reddit_sentiments,
        "news": news_sentiments,
        "reddit_avg": reddit_avg,
        "news_avg": news_avg,
        "reddit_stats": reddit_stats,
        "news_stats": news_stats
    })

@app.route('/api/data')
def get_data():
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)