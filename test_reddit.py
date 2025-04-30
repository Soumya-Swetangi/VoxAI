import praw
reddit = praw.Reddit(
    client_id="3WyjMcNGIxxcZ72g6qBzrg",
    client_secret="BdtzJ07zEIYYASpn_dRUEspBoWXJRg",
    user_agent="public-opinion-tracker/1.0"
)
print(list(reddit.subreddit("all").search("LPU", limit=1)))