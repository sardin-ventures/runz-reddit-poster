#!/usr/bin/env python3
"""Posts the RUNZ studio's own hand-written Reddit posts from the studio account.

Credentials live in the macOS keychain (service `runz-reddit`, accounts
`client_id`, `client_secret`, `post_refresh_token`); nothing is stored in code.

  reddit_post.py auth-url                  # mobile-friendly; log in as the studio account, Allow, copy the URL you land on
  reddit_post.py token '<callback url>'    # stores the posting refresh token
  reddit_post.py whoami
  reddit_post.py rules <sub>               # sidebar rules + post requirements + flairs
  reddit_post.py link  <sub> <title> <url> [--flair ID] [--comment FILE]
  reddit_post.py text  <sub> <title> <body file> [--flair ID] [--comment FILE]
  reddit_post.py video <sub> <title> <mp4> [--poster PNG] [--flair ID] [--comment FILE]
  reddit_post.py gif   <sub> <title> <gif|mp4> [--flair ID] [--comment FILE]
  reddit_post.py image <sub> <title> <png|jpg> [--flair ID] [--comment FILE]
  reddit_post.py comment <post id|url> <body file>
  reddit_post.py log                       # what this tool has posted (posted_log.jsonl)
"""
import argparse, datetime, json, os, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = 'runz-reddit'
REDIRECT_URI = 'https://theo-sardin.github.io/runz-media/'

SCOPES = 'identity submit read flair edit history'
UA = 'macos:runz-organic:0.1 (by Sardin Ventures)'
LOG = os.path.join(HERE, 'posted_log.jsonl')


def kc_get(account):
    return subprocess.run(['security', 'find-generic-password', '-s', SERVICE, '-a', account, '-w'],
                          capture_output=True, text=True, check=True).stdout.strip()


def kc_set(account, value):
    subprocess.run(['security', 'add-generic-password', '-U', '-s', SERVICE, '-a', account, '-w', value], check=True)


def reddit():
    import praw
    return praw.Reddit(client_id=kc_get('client_id'), client_secret=kc_get('client_secret'),
                       refresh_token=kc_get('post_refresh_token'), user_agent=UA)


def log(entry):
    entry['at'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    with open(LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def finish(r, kind, sub, title, post, comment_file):
    out = {'kind': kind, 'sub': sub, 'title': title, 'id': post.id if post else None,
           'url': f'https://www.reddit.com{post.permalink}' if post else None}
    if post and comment_file:
        c = post.reply(open(comment_file).read())
        out['comment'] = c.id
    log(out)
    print(json.dumps(out, indent=1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('cmd')
    p.add_argument('args', nargs='*')
    p.add_argument('--flair')
    p.add_argument('--comment')
    p.add_argument('--poster')
    a = p.parse_args()

    if a.cmd == 'auth-url':
        q = urllib.parse.urlencode({'client_id': kc_get('client_id'), 'response_type': 'code', 'state': 'runz-organic',
                                    'redirect_uri': REDIRECT_URI, 'duration': 'permanent', 'scope': SCOPES})
        print('https://www.reddit.com/api/v1/authorize.compact?' + q)
        return
    if a.cmd == 'token':
        import requests
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(a.args[0]).query)
        if 'code' not in qs:
            sys.exit(f'no code in the URL: {qs}')
        resp = requests.post('https://www.reddit.com/api/v1/access_token',
                             auth=(kc_get('client_id'), kc_get('client_secret')), headers={'User-Agent': UA},
                             data={'grant_type': 'authorization_code', 'code': qs['code'][0], 'redirect_uri': REDIRECT_URI})
        tok = resp.json()
        if resp.status_code != 200 or 'refresh_token' not in tok:
            sys.exit(f'token exchange failed ({resp.status_code}): {resp.text[:300]}')
        kc_set('post_refresh_token', tok['refresh_token'])
        print('stored posting token; scopes:', tok.get('scope'))
        return
    if a.cmd == 'log':
        print(open(LOG).read() if os.path.exists(LOG) else '(nothing posted yet)')
        return

    r = reddit()
    if a.cmd == 'whoami':
        me = r.user.me()
        print(json.dumps({'name': me.name, 'link_karma': me.link_karma, 'comment_karma': me.comment_karma,
                          'created_utc': me.created_utc, 'verified_email': getattr(me, 'has_verified_email', None)}))
    elif a.cmd == 'rules':
        s = r.subreddit(a.args[0])
        print('subscribers:', s.subscribers, '| type:', s.subreddit_type, '| submission_type:', s.submission_type,
              '| media:', getattr(s, 'allow_videos', None), getattr(s, 'allow_images', None))
        for rule in s.rules:
            print(f'- {rule.short_name}: {rule.description[:400]}')
        try:
            print('requirements:', json.dumps(s.post_requirements()))
        except Exception as e:  # some subs hide it
            print('requirements: n/a', e)
        try:
            for f in s.flair.link_templates.user_selectable():
                print('flair:', f['flair_template_id'], f['flair_text'])
        except Exception as e:
            print('flairs: n/a', e)
    elif a.cmd in ('link', 'text', 'video', 'gif', 'image'):
        sub, title, arg = a.args[0], a.args[1], a.args[2]
        s = r.subreddit(sub)
        kw = {'flair_id': a.flair} if a.flair else {}
        if a.cmd == 'link':
            post = s.submit(title, url=arg, **kw)
        elif a.cmd == 'text':
            post = s.submit(title, selftext=open(arg).read(), **kw)
        elif a.cmd == 'video':
            post = s.submit_video(title, arg, thumbnail_path=a.poster, without_websocket=False, **kw)
        elif a.cmd == 'gif':
            post = s.submit_video(title, arg, videogif=True, thumbnail_path=a.poster, without_websocket=False, **kw)
        else:
            post = s.submit_image(title, arg, without_websocket=False, **kw)
        finish(r, a.cmd, sub, title, post, a.comment)
    elif a.cmd == 'comment':
        target = a.args[0]
        sub = r.submission(url=target) if target.startswith('http') else r.submission(id=target)
        c = sub.reply(open(a.args[1]).read())
        log({'kind': 'comment', 'on': sub.id, 'id': c.id})
        print('commented', c.id)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
