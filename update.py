import argparse
import itertools
import json
import spotipy
import spotipy.util as util
from categories import CATEGORIES
from utils import page

try:
    from client import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
except ImportError:
    print("Error: Before using this, copy client.example to client.py and fill in its blanks")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('username')
args = parser.parse_args()
username = args.username

token = util.prompt_for_user_token(username=args.username, scope='playlist-read-private',
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)
if not token:
    print("Can't get token for", username)
    exit(1)
sp = spotipy.Spotify(auth=token)
user_id = sp.current_user()['id']

playlists = {}  # name: id

@page(sp)
def compile_playlists(result):
    for item in result['items']:
        if item['owner']['id'] != user_id:
            continue
        playlists[item['name']] = item['id']

@page(sp)
def compile_track_ids(result, track_ids):
    track_ids.extend(item['track']['id'] for item in result['items'] if item['track']['id'] is not None)

result = sp.current_user_playlists()
compile_playlists(result)

for name, playlist_names in CATEGORIES.items():
    objs = []

    for playlist_name in playlist_names:
        try:
            playlist_id = playlists[playlist_name]
        except KeyError:
            print("Warning: no playlist called '{}' found".format(playlist_name))
            continue

        print("Working on [{}] {}...".format(playlist_id, playlist_name))

        obj =  {'id': playlist_id, 'name': playlist_name}
        track_ids = []
        result = sp.user_playlist_tracks(username, playlist_id)
        compile_track_ids(result, track_ids)
        obj['track_ids'] = track_ids

        objs.append(obj)

    fp = open(name, 'w')
    json.dump(objs, fp, indent=2)
    fp.close()
