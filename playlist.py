import argparse
import json
import spotipy
from utils import page

try:
    from client import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SPOTIFY_USERNAME
except ImportError:
    print("Error: Before using this, copy client.example to client.py and fill in its blanks")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('playlist_id')
parser.add_argument('--username', '-u', default=SPOTIFY_USERNAME,
    help="Username of Spotify account to use. (default: %s)" % SPOTIFY_USERNAME)
parser.add_argument('--spreadsheet-id', default=None,
    help="Google Spreadsheet ID to insert collated data into. Experimental.")
parser.add_argument('--quiet', '-q', default=False, action='store_true',
    help="Don't print the information to the console")
parser.add_argument('--named', '-n', default=False, action='store_true',
    help="Interpret the playlist ID as a name, not a Spotify URI")
args = parser.parse_args()

username = args.username
playlist_id = args.playlist_id

if args.named:
    # Try to find a cached playlist with this name
    found = False
    for category in ['genre', 'tempo', 'special']:
        fp = open(category + '.json')
        objs = json.load(fp)
        fp.close()
        for obj in objs:
            if "WCS " + playlist_id == obj['name'] or playlist_id == obj['name']:
                playlist_id = obj['id']
                found = True
                break
        if found:
            break
    if not found:
        print("Can't find ID for name:", playlist_id)
        exit(1)

token = spotipy.prompt_for_user_token(username=args.username, client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)
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
def get_tracks_info(result):
    infos = []

    items = result['items']
    track_ids = [item['track']['id'] for item in items if item['track']['id'] is not None]
    features_by_track_id = {feature['id']: feature for feature in sp.audio_features(track_ids)}

    for i, item in enumerate(items, start=1):
        track = item['track']
        features = features_by_track_id.get(track['id'])
        info = get_track_info(track, features)
        infos.append(info)

        if not args.quiet:
            print(f"{i:3d} | {info['name'][:35]:35s} | {info['artist'][:25]:25s} | "
                  f"{info['tempo_range']:>6s} {info['tempo']:3.0f} | "
                  f"{info['release']:^4s} | {info['genres']:s}")

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
    info['release'] = track['album']['release_date'][:4] if track['album']['release_date'] else '-'
    info['genres'] = ", ".join(find_playlists('genre.json', track_id))
    info['special'] = ", ".join(find_playlists('special.json', track_id))

    return info


playlist_name = sp.user_playlist(username, playlist_id)['name']
print("Getting playlist:", playlist_name)

result = sp.user_playlist_tracks(username, playlist_id)
infos = get_tracks_info(result)

values = [["#", "Name", "Artist", "BPM list", "BPM", "Release", "Genres", "Special"]]
keys = ['name', 'artist', 'tempo_range', 'tempo', 'release', 'genres', 'special']
for i, info in enumerate(infos):
    values.append([i] + [info[key] for key in keys])

if args.spreadsheet_id:

    # This part is taken from the quickstart:
    # https://developers.google.com/sheets/api/quickstart/python
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import os.path
    import pickle

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'google-credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)
    range_name = "'{}'!A1".format(playlist_name)

    result = service.spreadsheets().values().append(
        spreadsheetId=args.spreadsheet_id, range=range_name,
        valueInputOption='RAW', body={'values': values}).execute()
