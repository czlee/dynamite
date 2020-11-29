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


def print_track_info(item):
    track = item.track
    artists = format_artists(track.artists)
    print(f"\033[1;36m{track.name}")
    print(f"\033[0;36m{artists}\033[0m")
    print(f"[spotify:track:{track.id}]")
    print(f"album released: \033[1;35m{track.album.release_date}\033[0m")
    print(f"added to playlist: {item.added_at}")

    features = sp.track_audio_features(track.id)
    nearest_tempo_list = int(round(clip_tempo(features.tempo), ndigits=-1))
    print(f"Spotify-reported tempo: \033[1;35m{features.tempo:.1f} bpm\033[0m, nearest list: {nearest_tempo_list}bpm")

    already_in = all_cached_playlists.playlists_containing_track(track.id)
    if already_in:
        print(f"\033[0;33mThis track is already in:\033[0m")
        for playlist in already_in:
            print(f" - {playlist.name}")


def update_cache(filename, playlists):
    fp = open(filename, 'w')
    json.dump(playlists.serialize(), fp, indent=2)
    fp.close()


def check_then_add_to_playlist(playlist, track):
    if playlist.contains_track(track):
        print(f"✓ already in {playlist.name}")
    else:
        sp.playlist_add(playlist.id, ["spotify:track:" + track.id])
        print(f"\033[0;32m→ added to {playlist.name}\033[0m")
        playlist.add_track_id(track.id)


def add_to_tempo_playlist(track):
    user_tempo = input("Which tempo list? ")
    playlist = tempo_playlists.playlist_by_name(f"WCS {user_tempo}bpm") or tempo_playlists.playlist_by_name(f"WCS {user_tempo}")
    while playlist is None and user_tempo not in ["s", "skip"]:
        user_tempo = input("  \033[0;33m✘ Invalid tempo.\033[0m Type 'skip' to skip, or pick a tempo list: ")
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
            genre = input(f"\033[0;33mPlaylist \"WCS {genre}\" not found.\033[0m Try again? ")
            continue
        check_then_add_to_playlist(playlist, track)
        genre = input("Any other genres? ")
    update_cache('genre.json', genre_playlists)


def add_to_wcs_all(track):
    check_then_add_to_playlist(all_playlist, track)


def sort_item(item):
    track = item.track
    print_track_info(item)
    sp.playback_start_tracks([track.id], position_ms=15000)
    add_to_tempo_playlist(track)
    add_to_genre_playlist(track)
    add_to_wcs_all(track)

    if args.remove_after_sort:
        sp.playlist_remove(playlist_id, ["spotify:track:" + track.id])
        print(f"\033[0;31m←\033[0m removed from {playlist.name}")

    print()


scope = tekore.Scope(tekore.scope.user_modify_playback_state, tekore.scope.playlist_modify_public)
if args.remove_after_sort:
    scope += tekore.scope.playlist_modify_private

sp = get_spotify_object(args.tekore_cfg, scope=scope)
playlist_id = parse_playlist_arg(args.playlist)
playlist = sp.playlist(playlist_id)
print(f"\033[1;34mSorting playlist: {playlist.name}\033[0;34m [{playlist.id}]\033[0m\n")

all_cached_playlists = cached.all_cached_playlists()
all_cached_playlists.remove_playlist(playlist_id)
tempo_playlists = cached.CachedPlaylistGroup.from_filename('tempo.json')
genre_playlists = cached.CachedPlaylistGroup.from_filename('genre.json')
all_playlist = cached.CachedPlaylist.from_playlist_id(ALL_PLAYLIST_ID, sp, expected_name=ALL_PLAYLIST_NAME)

items = sp.all_items(playlist.tracks)
for item in items:
    sort_item(item)


