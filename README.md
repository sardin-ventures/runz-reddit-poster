# runz-reddit-poster

A small command-line tool that the two developers of **RUNZ** (an indie roguelite on Steam, by [sardin-ventures](https://sardin-ventures.github.io/runz/)) use to publish their **own** posts from their **own** studio account, instead of copy-pasting from a phone.

## What it does
- Submits a post we wrote ourselves (text, link, image, GIF or video) to one subreddit, with the flair the subreddit asks for.
- Adds our first comment under that post (links, dev notes).
- Reads a subreddit's rules, post requirements and flairs before we post, so we follow them.
- Reads our own account info (`whoami`) and keeps a local log of what we posted.

## What it never does
- No voting, no messaging, no following, no scraping, no reading other users' data.
- No posting from any account other than the studio's own.
- No bulk or scheduled spam: at most 3 posts a day across all subreddits, at least 3 hours apart, each one written and reviewed by a human, and only in subreddits whose rules allow it.

## Scopes
`identity submit read flair edit history`, for one account (ours), via OAuth with a refresh token stored in the macOS keychain. Expected volume: well under 100 API calls a day.

## Usage
```
python3 reddit_post.py rules <sub>
python3 reddit_post.py text  <sub> "<title>" body.md --flair <id> --comment comment.md
python3 reddit_post.py video <sub> "<title>" clip.mp4 --flair <id> --comment comment.md
python3 reddit_post.py log
```
Requires `praw` and `requests` (`pip install -r requirements.txt`).

## Contact
sardin.ventures@gmail.com
