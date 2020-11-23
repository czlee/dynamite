import argparse
import json
import re
import spotipy
from utils import page

try:
    from client import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SPOTIFY_USERNAME
except ImportError:
    print("Error: Before using this, copy client.example to client.py and fill in its blanks")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('playlist',
    help="Playlist to show, specify by either name or ID")
parser.add_argument('--username', '-u', default=SPOTIFY_USERNAME,
    help="Username of Spotify account to use. (default: %s)" % SPOTIFY_USERNAME)
parser.add_argument('--quiet', '-q', default=False, action='store_true',
    help="Don't print the information to the console")
parser.add_argument('--no-bpm-clip', '-B', default=True, action='store_false', dest='bpm_clip',
    help="Don't clip BPMs to be between 60 and 140")
parser.add_argument('--release-date-precision', '-r', default='year', choices=['year', 'month', 'day'],
    help="Display release date to this level of precistion")
args = parser.parse_args()

username = args.username

def find_cached_playlist(name):
    """Returns the ID of the playlist with this name, if it's in the playlist
    cache. Returns None if no such ID found."""

    for category in ['genre', 'tempo', 'status', 'special']:
        fp = open(category + '.json')
        objs = json.load(fp)
        fp.close()
        for obj in objs:
            if "WCS " + name == obj['name'] or name == obj['name']:
                return obj['id']
    return None

playlist_id = find_cached_playlist(args.playlist)
if playlist_id is None:
    if re.match(r'[0-9A-Za-z]{22}', args.playlist[-22:]):
        playlist_id = args.playlist
    else:
        print("Couldn't find in the playlist cache, and this doesn't look like a playlist ID either:")
        print("    " + args.playlist)
        exit(1)


token = spotipy.prompt_for_user_token(username=args.username, client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)
if not token:
    print("Can't get token for", username)
    exit(1)
sp = spotipy.Spotify(auth=token)

def clip_tempo(tempo):
    if not args.bpm_clip:
        return tempo
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
def get_tracks_info(result):
    infos = []

    items = result['items']
    track_ids = [item['track']['id'] for item in items if item['track']['id'] is not None]
    features_by_track_id = {feature['id']: feature for feature in sp.audio_features(track_ids)}

    for item in items:
        track = item['track']
        features = features_by_track_id.get(track['id'])
        info = get_track_info(track, features)
        infos.append(info)

    return infos

def get_track_info(track, features=None):
    track_id = track['id']

    if not features and track_id:
        features = sp.audio_features(track_id)[0]

    info = {}
    info['name'] = track['name']
    info['artist'] = ", ".join(x['name'] for x in track['artists'])
    info['tempo_range'] = " ".join(find_playlists('tempo.json', track_id))
    info['tempo'] = clip_tempo(features['tempo']) if features else 0
    info['release'] = format_release_date(track['album']['release_date'])
    info['genres'] = ", ".join(find_playlists('genre.json', track_id))
    info['special'] = ", ".join(find_playlists('special.json', track_id))

    return info

def format_release_date(release_date, precision=args.release_date_precision):
    """Formats release date according to user argument"""
    length = {'year': 4, 'month': 7, 'day': 10}[precision]
    if release_date is None:
        return '-'.ljust(length)
    return release_date[:length].ljust(length)


playlist_name = sp.user_playlist(username, playlist_id)['name']
print("Getting playlist:", playlist_name)

result = sp.user_playlist_tracks(username, playlist_id)
infos = get_tracks_info(result)

values = [["#", "Name", "Artist", "BPM list", "BPM", "Release", "Genres", "Special"]]
keys = ['name', 'artist', 'tempo_range', 'tempo', 'release', 'genres', 'special']
for i, info in enumerate(infos, start=1):
    values.append([i] + [info[key] for key in keys])

    if not args.quiet:
        print(f"{i:3d} | {info['name'][:35]:35s} | {info['artist'][:25]:25s} | "
              f"{info['tempo_range']:>6s} {info['tempo']:3.0f} | "
              f"{info['release']:^4s} | {info['genres']:s}")
