"""Removes all songs on the playlist 'WCS removed' from all other WCS playlists.

Runs a dry run (i.e. does not delete) by default. Use --confirm-remove to
actually remove the tracks."""

import argparse
import json
import spotipy
import datetime
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
parser.add_argument('--output-file', '-O', default='removed.log', type=argparse.FileType('a'),
    help="Record removed tracks here (used only if --confirm-remove specified)")
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

removed_track_result = sp.user_playlist_tracks(username, REMOVED_PLAYLIST_ID)
removed_track_data = {x['track']['id']: {
        'name': x['track']['name'],
        'artist': ", ".join(x['name'] for x in x['track']['artists']),
    } for x in removed_track_result['items']}
removed_track_ids = set(removed_track_data.keys())
removed_track_playlists = {track_id: [] for track_id in removed_track_ids}

def handle_playlist(playlist_id, playlist_name):
    actual_name = sp.user_playlist(username, playlist_id)['name']
    if playlist_name != actual_name:
        print(f"Playlist names don't match: expected name {playlist_name}, actual name {actual_name}")
        return

    print(" " * 80, end="\r")
    print(f"Checking playlist: {playlist_name}...", end="\r")

    result = sp.user_playlist_tracks(username, playlist_id)
    playlist_track_ids = {x['track']['id'] for x in result['items']}
    found_in_playlist = removed_track_ids & playlist_track_ids

    if not found_in_playlist:
        return

    for track_id in found_in_playlist:
        removed_track_playlists[track_id].append((playlist_id, playlist_name))

    if args.confirm_remove:
        sp.playlist_remove_all_occurrences_of_items(playlist_id, found_in_playlist)

def log_output(message):
    print(message)
    if args.confirm_remove:
        args.output_file.write(message + "\n")


log_output("=== " + datetime.datetime.now().isoformat() + " ===")

handle_playlist(ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME)

for filename in CATEGORIES.keys():
    playlists = json.load(open(filename))
    for playlist in playlists:
        handle_playlist(playlist['id'], playlist['name'])

for track_id, track_data in removed_track_data.items():
    if len(removed_track_playlists[track_id]) == 0:
        continue

    remove_string = "Removed" if args.confirm_remove else "Would remove"
    log_output("{remove_string} [spotify:track:{track_id}] \"{name}\" ({artist}), which was in:".format(
        remove_string=remove_string,
        name=removed_track_data[track_id]['name'],
        artist=removed_track_data[track_id]['artist'],
        track_id=track_id,
    ))
    for playlist_id, playlist_name in removed_track_playlists[track_id]:
        log_output(f" - [spotify:playlist:{playlist_id}] {playlist_name}")

log_output("")

if not args.confirm_remove:
    print("Use --confirm-remove to follow through with the removal.")
