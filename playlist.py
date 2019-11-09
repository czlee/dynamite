import argparse
import json
import spotipy
import spotipy.util as util
from client import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from utils import page

parser = argparse.ArgumentParser()
parser.add_argument('username')
parser.add_argument('playlist_id')
args = parser.parse_args()

username = args.username
playlist_id = args.playlist_id

token = util.prompt_for_user_token(username=args.username, scope='playlist-read-private',
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)
if not token:
    print("Can't get token for", username)
    exit(1)
sp = spotipy.Spotify(auth=token)

def clip_tempo(tempo):
    if tempo < 60:
        return tempo * 2
    elif tempo > 140:
        return tempo / 2
    else:
        return tempo

def find_playlists(file, track_id):
    fp = open(file)
    objs = json.load(fp)
    fp.close()
    names = []
    for obj in objs:
        if track_id in obj['track_ids']:
            name = obj['name'][4:] if obj['name'].startswith("WCS ") else obj['name']
            names.append(name)
    return names

@page(sp)
def show_tracks(result):
    items = result['items']
    track_ids = [item['track']['id'] for item in items]
    features = sp.audio_features(track_ids)

    for i, (item, feature) in enumerate(zip(items, features), start=1):
        track = item['track']
        artist = ", ".join(x['name'] for x in track['artists'])
        name = track['name']
        tempo_range = " ".join(find_playlists('tempo.json', track['id']))
        tempo = clip_tempo(feature['tempo'])
        genres = ", ".join(find_playlists('genre.json', track['id']))
        release = track['album']['release_date'][:4]
        print(f"{i:3d} | {name[:35]:35s} | {artist[:25]:25s} | {tempo_range:>6s} {tempo:3.0f} | {release:s} | {genres:s}")

result = sp.user_playlist_tracks(args.username, args.playlist_id)
show_tracks(result)
