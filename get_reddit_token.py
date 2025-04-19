import praw
import webbrowser

# Replace with your app's details
client_id = '3WyjMcNGIxxcZ72g6qBzrg'  # From Reddit app
client_secret = 'BdtzJ07zEIYYASpn_dRUEspBoWXJRg'  # From Reddit app
redirect_uri = 'http://localhost:8080'
user_agent = 'Soumya Swetangi/1.0 by Inner-Band5591'  # Use your Reddit username

# Initialize Reddit instance
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    user_agent=user_agent
)

# Generate authorization URL
url = reddit.auth.url(scopes=['read'], state='random_string', duration='permanent')
print(f"Opening browser to: {url}")
webbrowser.open(url)

# After authorizing, copy the 'code' from the redirect URL
code = input("Enter the code from the redirect URL (e.g., abc123...): ")

# Exchange code for refresh token
refresh_token = reddit.auth.authorize(code)
print(f"Your refresh token is: {refresh_token}")