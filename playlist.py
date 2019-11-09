import argparse
import json
import spotipy
import spotipy.util as util
from utils import page

try:
    from client import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
except ImportError:
    print("Error: Before using this, copy client.example to client.py and fill in its blanks")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('username')
parser.add_argument('playlist_id')
parser.add_argument('spreadsheet_id', nargs='?', default=None)
parser.add_argument('--quiet', '-q', default=False, action='store_true')
parser.add_argument('--named', '-n', default=False, action='store_true')
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
def process_tracks(result, values):
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
        special = ", ".join(find_playlists('special.json', track['id']))
        release = track['album']['release_date'][:4]

        values.append([i, name, artist, tempo_range, tempo, release, genres, special])
        if not args.quiet:
            print(f"{i:3d} | {name[:35]:35s} | {artist[:25]:25s} | {tempo_range:>6s} "
                  f"{tempo:3.0f} | {release:s} | {genres:s}")

playlist_name = sp.user_playlist(username, playlist_id)['name']
print("Getting playlist:", playlist_name)

values = [
    ["#", "Name", "Artist", "BPM list", "BPM", "Release", "Genres", "Special"],
]
result = sp.user_playlist_tracks(username, playlist_id)
process_tracks(result, values)

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
