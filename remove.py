"""Removes all songs on the playlist 'WCS removed' from all other WCS playlists.

Runs a dry run (i.e. does not delete) by default. Use --confirm-remove to
actually remove the tracks."""

import argparse
import json
import spotipy
from categories import CATEGORIES

try:
    from client import (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SPOTIFY_USERNAME,
                        REMOVED_PLAYLIST_ID, REMOVED_PLAYLIST_NAME, ALL_PLAYLIST_ID,
                        ALL_PLAYLIST_NAME)
except ImportError:
    print("Error: Before using this, copy client.example to client.py and fill in its blanks")
    exit(1)

parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
parser.add_argument('--username', '-u', default=SPOTIFY_USERNAME,
    help=f"Username of Spotify account to use. (default: {SPOTIFY_USERNAME})")
parser.add_argument('--confirm-remove', action='store_true', default=False,
    help="Actually remove the tracks")
args = parser.parse_args()

username = args.username
token = spotipy.prompt_for_user_token(username=username, client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)
if not token:
    print("Can't get token for", username)
    exit(1)
sp = spotipy.Spotify(auth=token)

removed_playlist = sp.user_playlist(username, REMOVED_PLAYLIST_ID)
assert removed_playlist['name'] == REMOVED_PLAYLIST_NAME

all_playlist = sp.user_playlist(username, ALL_PLAYLIST_ID)
assert all_playlist['name'] == ALL_PLAYLIST_NAME

result = sp.user_playlist_tracks(username, REMOVED_PLAYLIST_ID)
removed_track_ids = {x['track']['id'] for x in result['items']}

def handle_playlist(playlist_id, playlist_name):
    actual_name = sp.user_playlist(username, playlist_id)['name']
    if playlist_name != actual_name:
        print(f"Playlist names don't match: expected name {playlist_name}, actual name {actual_name}")
        return
    result = sp.user_playlist_tracks(username, playlist_id)
    playlist_track_names = {x['track']['id']: x['track']['name'] for x in result['items']}
    playlist_track_ids = set(playlist_track_names.keys())
    found_in_playlist = removed_track_ids & playlist_track_ids

    if found_in_playlist:
        if args.confirm_remove:
            print(f"Would remove from {playlist_name}:")
        else:
            print(f"Removing from {playlist_name}:")
        for track_id in found_in_playlist:
            print("  - " + playlist_track_names[track_id])


handle_playlist(ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME)

for filename in CATEGORIES.keys():
    playlists = json.load(open(filename))
    for playlist in playlists:
        handle_playlist(playlist['id'], playlist['name'])

if not args.confirm_remove:
    print("Use --confirm-remove to follow through with the removal.")