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
import re
from collections import Counter
import time

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

# Gemini API setup
GEMINI_API_KEY = os.getenv("AIzaSyAUC9UsobKFpp9lMp0RYlz66jqO1A3Befo")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
# Validate environment variables
missing_keys = []
for key in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "NEWS_API_KEY", "GEMINI_API_KEY"]:
    if not os.getenv(key):
        missing_keys.append(key)
if missing_keys:
    logging.warning(f"Missing environment variables: {', '.join(missing_keys)}. Some features may not work.")

# Initialize sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Cache for fetched data (topic -> sentiments, timestamp)
data_cache = {}
CACHE_DURATION = 3600  # Cache for 1 hour

# Store sentiments globally
sentiments = {'reddit': [], 'news': []}

def fetch_reddit_posts(topic):
    try:
        subreddit = reddit.subreddit('all').search(topic, limit=10)
        posts = []
        for submission in subreddit:
            score = analyzer.polarity_scores(submission.title)
            body = submission.selftext[:1000] if submission.selftext else ""
            text = f"{submission.title} {body}".strip()
            posts.append({
                'text': text,
                'compound': score['compound'],
                'pos': score['pos'],
                'neg': score['neg'],
                'neu': score['neu'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'reddit'
            })
        logging.debug(f"Fetched {len(posts)} Reddit posts for topic: {topic}")
        return posts
    except Exception as e:
        logging.error(f"Reddit fetch error for topic {topic}: {str(e)}")
        return []

def fetch_news_articles(topic):
    try:
        url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={NEWS_API_KEY}&language=en&sortBy=publishedAt&pageSize=10"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'articles' not in data:
            logging.error(f"No 'articles' key in News API response for topic {topic}: {data}")
            return []
        articles = data.get('articles', [])
        news = []
        for article in articles:
            title = article.get('title', '')
            description = article.get('description', '')[:1000] or ''
            if title:
                score = analyzer.polarity_scores(title)
                text = f"{title} {description}".strip()
                news.append({
                    'text': text,
                    'compound': score['compound'],
                    'pos': score['pos'],
                    'neg': score['neg'],
                    'neu': score['neu'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'news'
                })
        logging.debug(f"Fetched {len(news)} news articles for topic: {topic}")
        return news
    except Exception as e:
        logging.error(f"News fetch error for topic {topic}: {str(e)}")
        return []

def clean_text(text):
    """Clean text for NLP processing."""
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^\w\s.]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def gemini_summarize(text):
    """Call Gemini API for summarization."""
    if not GEMINI_API_KEY:
        logging.warning("Gemini API key not set, skipping summarization")
        return None
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": f"Provide a concise summary (50-200 words) of the following text, focusing on key points and public sentiment: {text[:2000]}"}]
            }]
        }
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        logging.debug(f"Sending Gemini API request for summarization: {url}")
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        logging.debug(f"Gemini API response: {result}")
        if "candidates" in result and result["candidates"]:
            summary = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            logging.debug(f"Gemini summarization successful: {summary[:100]}...")
            return summary
        else:
            logging.warning("No valid summary returned by Gemini API")
            return None
    except Exception as e:
        logging.warning(f"Gemini summarization failed: {str(e)}")
        return None

def gemini_extract_themes(text):
    """Call Gemini API to extract analytical themes."""
    if not GEMINI_API_KEY:
        logging.warning("Gemini API key not set, skipping theme extraction")
        return []
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": f"Identify 3-5 key themes or entities driving public sentiment in the following text, returning them as a comma-separated list (e.g., 'climate change, renewable energy, emissions'): {text[:1000]}"}]
            }]
        }
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        logging.debug(f"Sending Gemini API request for theme extraction: {url}")
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        logging.debug(f"Gemini API response: {result}")
        if "candidates" in result and result["candidates"]:
            themes = result["candidates"][0]["content"]["parts"][0]["text"].strip().split(",")
            themes = [theme.strip() for theme in themes if len(theme.strip()) > 3]
            logging.debug(f"Gemini theme extraction successful: {themes}")
            return themes[:3]
        else:
            logging.warning("No valid themes returned by Gemini API")
            return []
    except Exception as e:
        logging.warning(f"Gemini theme extraction failed: {str(e)}")
        return []

def analyze_sentiment_drivers(posts, themes):
    """Analyze which themes are associated with positive or negative sentiment."""
    drivers = {'positive': [], 'negative': []}
    for post in posts:
        text = clean_text(post['text']).lower()
        for theme in themes:
            if theme.lower() in text:
                if post['compound'] > 0.2:
                    drivers['positive'].append(theme)
                elif post['compound'] < -0.2:
                    drivers['negative'].append(theme)
    return drivers

def extract_fallback_themes(texts):
    """Extract meaningful themes as a fallback if Gemini fails."""
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'that', 'this', 'is', 'are', 'was', 'were', 'be', 'been', 'will', 'about', 'from', 'as',
        'it', 'they', 'their', 'there', 'which', 'what', 'when', 'where', 'who', 'why', 'how',
        'according', 'some', 'many', 'other', 'such', 'just', 'only', 'also', 'very', 'more',
        'most', 'any', 'all', 'can', 'have', 'has', 'had', 'not'
    }
    words = [word.lower() for text in texts for word in clean_text(text).split() if word.lower() not in stopwords and len(word) > 4]
    word_counts = Counter(words)
    themes = [word for word, count in word_counts.most_common(5) if count > 1 and len(word) > 4]
    if not themes:
        themes = ['General Discussion', 'Public Opinion', 'Trends']
    logging.debug(f"Fallback themes extracted: {themes}")
    return themes[:3]

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
        # Check cache
        if topic in data_cache and (time.time() - data_cache[topic]['timestamp']) < CACHE_DURATION:
            logging.debug(f"Using cached data for {topic}")
            sentiments['reddit'] = data_cache[topic]['reddit']
            sentiments['news'] = data_cache[topic]['news']
            return jsonify({'reddit': sentiments['reddit'], 'news': sentiments['news']})

        # Fetch new data
        reddit_posts = fetch_reddit_posts(topic)
        news_articles = fetch_news_articles(topic)
        sentiments['reddit'] = reddit_posts
        sentiments['news'] = news_articles

        # Update cache
        data_cache[topic] = {
            'reddit': reddit_posts,
            'news': news_articles,
            'timestamp': time.time()
        }

        logging.debug(f"Analyzed topic: {topic}, Reddit: {len(reddit_posts)}, News: {len(news_articles)}")
        return jsonify({'reddit': reddit_posts, 'news': news_articles})
    except Exception as e:
        logging.error(f"Analyze error for topic {topic}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/<topic>')
def get_insights(topic):
    try:
        # Get current sentiment data
        reddit_posts = sentiments.get('reddit', [])
        news_articles = sentiments.get('news', [])
        all_posts = reddit_posts + news_articles
        all_texts = [p['text'] for p in all_posts]
        combined_text = " ".join(clean_text(text) for text in all_texts)

        if not all_texts:
            return jsonify({
                'summary': f"No data available for {topic}.",
                'insights': "No insights available due to insufficient data.",
                'themes': [],
                'recommendations': [],
                'sentiment_metrics': {
                    'reddit': {'pos': 0, 'neg': 0, 'neu': 0},
                    'news': {'pos': 0, 'neg': 0, 'neu': 0}
                }
            })

        # Calculate average sentiments
        reddit_avg = sum(p['compound'] for p in reddit_posts) / len(reddit_posts) if reddit_posts else 0
        news_avg = sum(a['compound'] for a in news_articles) / len(news_articles) if news_articles else 0
        reddit_pos = sum(p['pos'] for p in reddit_posts) / len(reddit_posts) * 100 if reddit_posts else 0
        reddit_neg = sum(p['neg'] for p in reddit_posts) / len(reddit_posts) * 100 if reddit_posts else 0
        reddit_neu = sum(p['neu'] for p in reddit_posts) / len(reddit_posts) * 100 if reddit_posts else 0
        news_pos = sum(a['pos'] for a in news_articles) / len(news_articles) * 100 if news_articles else 0
        news_neg = sum(a['neg'] for a in news_articles) / len(news_articles) * 100 if news_articles else 0
        news_neu = sum(a['neu'] for a in news_articles) / len(news_articles) * 100 if news_articles else 0

        # Determine sentiment description
        sentiment_description = "mixed"
        if reddit_avg > 0.2 and news_avg > 0.2:
            sentiment_description = "generally positive"
        elif reddit_avg < -0.2 and news_avg < -0.2:
            sentiment_description = "generally negative"

        # Generate summary using Gemini API
        summary = f"Public sentiment on {topic} is {sentiment_description} (Reddit: {reddit_avg:.2f}, News: {news_avg:.2f})."
        if len(combined_text) > 100:
            summary_text = gemini_summarize(combined_text)
            if summary_text:
                summary = summary_text
            else:
                summary = f"Overview of {topic} based on recent discussions and articles. Sentiment is {sentiment_description} (Reddit: {reddit_avg:.2f}, News: {news_avg:.2f})."

        # Extract themes using Gemini API
        themes = gemini_extract_themes(combined_text)
        if not themes:
            themes = extract_fallback_themes(all_texts)
            logging.debug(f"Fell back to keyword extraction for themes: {themes}")

        # Analyze sentiment drivers
        sentiment_drivers = analyze_sentiment_drivers(all_posts, themes)

        # Generate analytical insights
        insights = []
        insights.append(f"Public sentiment on {topic} is {sentiment_description}. Reddit shows a {reddit_pos:.1f}% positive, {reddit_neg:.1f}% negative, and {reddit_neu:.1f}% neutral sentiment, while news articles show {news_pos:.1f}% positive, {news_neg:.1f}% negative, and {news_neu:.1f}% neutral.")
        if sentiment_drivers['positive']:
            insights.append(f"Positive sentiment is driven by {', '.join(set(sentiment_drivers['positive']))}, reflecting optimism or approval.")
        if sentiment_drivers['negative']:
            insights.append(f"Negative sentiment is associated with {', '.join(set(sentiment_drivers['negative']))}, indicating concerns or criticism.")
        if abs(reddit_avg - news_avg) > 0.3:
            insights.append(f"There is a notable difference between Reddit (avg: {reddit_avg:.2f}) and news (avg: {news_avg:.2f}) sentiment, suggesting varied perspectives across platforms.")
        if themes:
            insights.append(f"Key discussion themes include {', '.join(themes)}, which dominate conversations and shape public perception.")
        if not insights:
            insights.append(f"Limited data for {topic} prevents detailed analysis, but sentiment is {sentiment_description}.")

        insights_text = " ".join(insights)

        # Enhance summary with themes
        if themes and summary_text:
            summary += f" Key themes include {', '.join(themes)}."

        # Generate recommended topics
        recommendations = []
        for theme in themes:
            recommendations.append(f"{theme} trends")
            recommendations.append(f"{theme} challenges")
        recommendations = list(set(recommendations))[:3]

        # Prepare sentiment metrics for the graph
        sentiment_metrics = {
            'reddit': {'pos': reddit_pos, 'neg': reddit_neg, 'neu': reddit_neu},
            'news': {'pos': news_pos, 'neg': news_neg, 'neu': news_neu}
        }

        logging.debug(f"Insights for {topic}: Summary: {summary}, Insights: {insights_text}, Themes: {themes}, Recommendations: {recommendations}, Sentiment Metrics: {sentiment_metrics}")
        return jsonify({
            'summary': summary,
            'insights': insights_text,
            'themes': themes,
            'recommendations': recommendations,
            'sentiment_metrics': sentiment_metrics
        })
    except Exception as e:
        logging.error(f"Insights error for topic {topic}: {str(e)}")
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
        csv_content = '\ufeff' + output.getvalue()
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
    app.run(host='0.0.0.0', port=5000, debug=True)