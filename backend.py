from flask import Flask, jsonify, render_template
from flask_cors import CORS
import praw
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json
import os
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__, template_folder='.', static_folder='static')
CORS(app)

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="public-opinion-tracker/1.0"
)
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
analyzer = SentimentIntensityAnalyzer()

DATA_FILE = "data.json"

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
                "timestamp": datetime.utcnow().isoformat(),
                "topic": topic
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
                    "timestamp": datetime.utcnow().isoformat(),
                    "topic": topic
                })
        return sentiments
    except Exception as e:
        print(f"News API error: {e}")
        return []

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze/<topic>')
def analyze_topic(topic):
    reddit_sentiments = get_reddit_sentiment(topic)
    news_sentiments = get_news_sentiment(topic)

    if not reddit_sentiments and not news_sentiments:
        return jsonify({"error": "No data found for this topic. Try a broader term."}), 404

    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    data['reddit'].extend(reddit_sentiments)
    data['news'].extend(news_sentiments)

    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

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
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"Data fetch error: {e}")
        return jsonify({"error": "Failed to load data"}), 500

@app.route('/api/trending')
def get_trending():
    trending = ["AI", "Election 2025", "Climate Change", "Cryptocurrency", "Space Exploration"]
    return jsonify({"trending": trending})

@app.route('/api/sentiment-overview')
def get_sentiment_overview():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        all_sentiments = data['reddit'] + data['news']
        if not all_sentiments:
            return jsonify({
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "total": 0
            })
        total = len(all_sentiments)
        positive = len([s for s in all_sentiments if s['compound'] > 0.05])
        negative = len([s for s in all_sentiments if s['compound'] < -0.05])
        neutral = len([s for s in all_sentiments if -0.05 <= s['compound'] <= 0.05])
        return jsonify({
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "total": total
        })
    except Exception as e:
        print(f"Sentiment overview error: {e}")
        return jsonify({"error": "Failed to compute sentiment overview"}), 500

@app.route('/api/trends')
def get_trends():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        all_sentiments = data['reddit'] + data['news']
        if not all_sentiments:
            print("No sentiment data found for trends")
            return jsonify({"trends": []})
        
        trends = {}
        for s in all_sentiments:
            try:
                timestamp = s.get('timestamp', '')
                if not timestamp or len(timestamp) < 10:
                    print(f"Invalid timestamp in sentiment: {s}")
                    continue
                date = timestamp[:10]  # YYYY-MM-DD
                if date not in trends:
                    trends[date] = {"sum": 0, "count": 0}
                trends[date]["sum"] += s['compound']
                trends[date]["count"] += 1
            except Exception as e:
                print(f"Error processing sentiment: {s}, error: {e}")
                continue
        
        if not trends:
            print("No valid trend data after processing")
            return jsonify({"trends": []})
            
        result = [
            {"date": date, "avg_sentiment": info["sum"] / info["count"]}
            for date, info in sorted(trends.items())
        ]
        print(f"Trends computed: {result}")
        return jsonify({"trends": result})
    except Exception as e:
        print(f"Trends error: {e}")
        return jsonify({"error": "Failed to compute trends"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
