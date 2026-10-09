#!/usr/bin/env python3
"""Post the weekly card to Instagram through the Graph API (needs IG_USER_ID and IG_ACCESS_TOKEN, a public image URL).
Two calls: create a media container from the URL, then publish it. Prints the media id."""
import json, os, sys, time, urllib.parse, urllib.request

def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

if __name__ == "__main__":
    user, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    image_url, caption = sys.argv[1], sys.argv[2]
    if not user or not token:
        print("no Instagram credentials; skipped"); sys.exit(0)
    base = f"https://graph.facebook.com/v21.0/{user}"
    c = post(f"{base}/media", {"image_url": image_url, "caption": caption, "access_token": token})
    time.sleep(5)  # the container needs a moment
    p = post(f"{base}/media_publish", {"creation_id": c["id"], "access_token": token})
    print(json.dumps(p))
