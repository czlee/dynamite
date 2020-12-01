"""Removes all songs on the playlist 'WCS removed' from all other WCS playlists.

Runs a dry run (i.e. does not delete) by default. Use --confirm-remove to
actually remove the tracks."""

import argparse
import datetime
import json

from categories import CATEGORIES
from settings import ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME, REMOVED_PLAYLIST_ID, REMOVED_PLAYLIST_NAME
from utils import format_artists, get_spotify_object

parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
parser.add_argument('--confirm-remove', action='store_true', default=False,
    help="actually remove the tracks")
parser.add_argument('--output-file', '-O', default='removed.log', type=argparse.FileType('a'),
    help="record removed tracks here (used only if --confirm-remove specified)")
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="file to use to store Tekore (Spotify) user token")
args = parser.parse_args()

sp = get_spotify_object(args.tekore_cfg)

removed_playlist = sp.playlist(REMOVED_PLAYLIST_ID)
assert removed_playlist.name == REMOVED_PLAYLIST_NAME

removed_items = list(sp.all_items(removed_playlist.tracks))
removed_track_ids = {item.track.id for item in removed_items}
removed_track_playlists = {track_id: [] for track_id in removed_track_ids}


def handle_playlist(playlist_id, playlist_name):
    playlist = sp.playlist(playlist_id)
    if playlist_name != playlist.name:
        print(f"Playlist names don't match: expected name {playlist_name}, actual name {playlist.name}")
        exit(1)

    print(" " * 80, end="\r")
    print(f"Checking playlist: {playlist_name}...", end="\r")

    playlist_items = sp.all_items(playlist.tracks)
    playlist_track_ids = {item.track.id for item in playlist_items}
    found_in_playlist = removed_track_ids & playlist_track_ids

    if not found_in_playlist:
        return

    for track_id in found_in_playlist:
        removed_track_playlists[track_id].append((playlist_id, playlist_name))

    if args.confirm_remove:
        sp.playlist_remove(playlist_id, ["spotify:track:" + track_id for track_id in found_in_playlist])


def log_output(message):
    print(message)
    if args.confirm_remove:
        args.output_file.write(message + "\n")


log_output("=== " + datetime.datetime.now().isoformat() + " ===")

handle_playlist(ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME)

for filename in CATEGORIES.keys():
    playlists = json.load(open(filename))
    for playlist in playlists:
        if playlist['id'] == REMOVED_PLAYLIST_ID:
            continue
        handle_playlist(playlist['id'], playlist['name'])

for item in removed_items:
    if len(removed_track_playlists[item.track.id]) == 0:
        continue

    remove_string = "Removed" if args.confirm_remove else "Would remove"
    log_output("{remove_string} [{track_id}] \"{name}\" ({artist}), which was in:".format(
        remove_string=remove_string,
        name=item.track.name,
        artist=format_artists(item.track.artists),
        track_id=item.track.id,
    ))
    for playlist_id, playlist_name in removed_track_playlists[item.track.id]:
        log_output(f" - [{playlist_id}] {playlist_name}")

log_output("")

if not args.confirm_remove:
    print("Use --confirm-remove to follow through with the removal.")
