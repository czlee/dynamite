"""Guides through the process of sorting a playlist into appropriate genre and
tempo playlists. After this is run, each track in the specified playlist should
be added to "WCS all", one of the WCS tempo playlists, and one or more of the
WCS genre playlists."""

import argparse
import json
import datetime
from categories import CATEGORIES

import tekore

import cached
from utils import clip_tempo, format_artists, format_release_date, format_tempo, get_spotify_object, parse_playlist_arg
from client import ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('playlist',
    help="Playlist to sort, specify by either name or ID")
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="File to use to store Tekore (Spotify) user token")
parser.add_argument("--remove-after-sort", action="store_true", default=False,
    help="Remove the track from this playlist after it is sorted")
args = parser.parse_args()


def show_track_info(item):
    track = item.track
    artists = format_artists(track.artists)
    print(f"\033[1;36m{track.name}")
    print(f"\033[0;36m{artists}\033[0m")
    print(f"\033[90mSpotify URI: spotify:track:{track.id}\033[0m")
    print(f"album released:    \033[1;36m{track.album.release_date}\033[0m")
    print(f"added to playlist: {item.added_at.strftime('%Y-%m-%d')}")

    features = sp.track_audio_features(track.id)
    nearest_tempo_list = int(round(clip_tempo(features.tempo), ndigits=-1))
    print(f"Spotify-reported tempo: \033[1;36m{features.tempo:.1f} bpm\033[0m, nearest list: {nearest_tempo_list}bpm")


def check_existing_playlists(track):
    """Checks whether this track is already in existing playlists.
    Returns True if it seems like this track is already fully sorted, False otherwise."""
    already_in = all_cached_playlists.playlists_containing_track(track.id)
    if not already_in:
        return False  # looks good

    in_tempo = False
    in_genre = False
    in_all = False

    print(f"\033[0;33mThis track is already in:\033[0m")
    for playlist in already_in:
        print(f" - {playlist.name}")
        if tempo_playlists.contains_playlist_id(playlist.id):
            in_tempo = True
        if genre_playlists.contains_playlist_id(playlist.id):
            in_genre = True
        if playlist.id == ALL_PLAYLIST_ID:
            in_all = True

    if not (in_tempo and in_genre and in_all):
        return False  # still got some sorting to do

    print("\033[0;33mLooks like this track is already fully sorted.\033[0m")
    response = input("Do you still want to sort this track? [y/n] ")
    while response not in ["y", "yes", "n", "no"]:
        response = input("\033[0;33m✘ Huh?\033[0m Type [y]es or [n]o: ")
    return response[0] == "n"


def update_cache(filename, playlists):
    fp = open(filename, 'w')
    json.dump(playlists.serialize(), fp, indent=2)
    fp.close()


def check_then_add_to_playlist(playlist, track):
    if playlist.contains_track(track):
        print(f"\033[0;35m✓ already in {playlist.name}\033[0m")
    else:
        sp.playlist_add(playlist.id, ["spotify:track:" + track.id])
        print(f"\033[0;32m→ added to {playlist.name}\033[0m")
        playlist.add_track_id(track.id)


def add_to_tempo_playlist(track):
    user_tempo = input("Which tempo list? ")
    playlist = tempo_playlists.playlist_by_name(f"WCS {user_tempo}bpm") or tempo_playlists.playlist_by_name(f"WCS {user_tempo}")
    while playlist is None and user_tempo not in ["s", "skip"]:
        user_tempo = input("\033[0;33m✘ Invalid tempo.\033[0m Type 'skip' to skip, or pick a tempo list: ")
        playlist = tempo_playlists.playlist_by_name(f"WCS {user_tempo}bpm") or tempo_playlists.playlist_by_name(f"WCS {user_tempo}")
    if user_tempo in ["s", "skip"]:
        return
    check_then_add_to_playlist(playlist, track)
    update_cache('tempo.json', tempo_playlists)


def add_to_genre_playlist(track):
    genre = input("Which genre list? ")
    while genre != "":
        playlist = genre_playlists.playlist_by_name(f"WCS {genre}")
        if playlist is None:
            genre = input(f"\033[0;33m✘ Playlist \"WCS {genre}\" not found.\033[0m Try again? ")
            continue
        check_then_add_to_playlist(playlist, track)
        genre = input("Any other genres? ")
    update_cache('genre.json', genre_playlists)


def add_to_wcs_all(track):
    check_then_add_to_playlist(all_playlist, track)


def remove_item(playlist, item):
    sp.playlist_remove(playlist_id, ["spotify:track:" + item.track.id])
    print(f"\033[0;31m←\033[0m removed from {playlist.name}")


def sort_item(item):
    track = item.track
    sp.playback_start_tracks([track.id], position_ms=15000)
    show_track_info(item)
    if check_existing_playlists(track):
        return
    add_to_tempo_playlist(track)
    add_to_genre_playlist(track)
    add_to_wcs_all(track)


scope = tekore.Scope(tekore.scope.user_modify_playback_state, tekore.scope.playlist_modify_public)
if args.remove_after_sort:
    scope += tekore.scope.playlist_modify_private

sp = get_spotify_object(args.tekore_cfg, scope=scope)
playlist_id = parse_playlist_arg(args.playlist)
playlist = sp.playlist(playlist_id)
print(f"\033[1;34mSorting playlist: {playlist.name}\033[0;34m [{playlist.id}]\033[0m\n")

tempo_playlists = cached.CachedPlaylistGroup.from_filename('tempo.json')
genre_playlists = cached.CachedPlaylistGroup.from_filename('genre.json')
all_playlist = cached.CachedPlaylist.from_playlist_id(ALL_PLAYLIST_ID, sp, expected_name=ALL_PLAYLIST_NAME)
all_cached_playlists = cached.all_cached_playlists()
all_cached_playlists.remove_playlist(playlist_id)
all_cached_playlists.add_playlist(all_playlist)

items = sp.all_items(playlist.tracks)
for item in items:
    sort_item(item)
    if args.remove_after_sort:
        remove_item(playlist, item)
    print() # blank line
