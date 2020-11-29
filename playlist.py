"""Retrieves and displays a given Spotify playlist with relevant additional data."""

import argparse
import json
import re
import tekore

from utils import format_artists, format_release_date, format_tempo, get_spotify_object

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('playlist',
    help="Playlist to show, specify by either name or ID")
parser.add_argument('--no-bpm-clip', '-B', default=True, action='store_false', dest='bpm_clip',
    help="Don't clip BPMs to be between 60 and 140")
parser.add_argument('--release-date-precision', '-r', default='year', choices=['year', 'month', 'day'],
    help="Display release date to this level of precision")
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="File to use to store Tekore (Spotify) user token")
args = parser.parse_args()

tempo_playlists = json.load(open('tempo.json'))
genre_playlists = json.load(open('genre.json'))

sp = get_spotify_object(args.tekore_cfg)


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

def find_playlists(playlists, track_id, exclude_id=None):
    names = []
    for playlist in playlists:
        if playlist['id'] == exclude_id:
            continue
        if track_id in playlist['track_ids']:
            name = playlist['name'][4:] if playlist['name'].startswith("WCS ") else playlist['name']
            names.append(name)
    return names

def get_tracks_info(items, playlist_id):
    infos = []

    items = list(items)
    track_ids = [item.track.id for item in items if item.track.id is not None]
    with sp.chunked(True):
        features = sp.tracks_audio_features(track_ids)
    features_by_track_id = {feature.id: feature for feature in features}

    for item in items:
        track = item.track
        info = get_track_info(track, playlist_id)

        features = features_by_track_id.get(track.id)
        info['tempo'] = format_tempo(features.tempo, clip=args.bpm_clip) if features else "-"

        infos.append(info)

    return infos

def get_track_info(track, playlist_id=None):
    info = {
        'name': track.name,
        'artist': format_artists(track.artists),
        'tempo_range': " ".join(find_playlists(tempo_playlists, track.id)),
        'release': format_release_date(track.album.release_date, args.release_date_precision),
        'genres': ", ".join(find_playlists(genre_playlists, track.id, exclude_id=playlist_id)),
    }
    return info


playlist_id = find_cached_playlist(args.playlist)
if playlist_id is None:
    if re.match(r'[0-9A-Za-z]{22}', args.playlist[-22:]):
        playlist_id = args.playlist
    else:
        print("Couldn't find in the playlist cache, and this doesn't look like a playlist ID either:")
        print("    " + args.playlist)
        exit(1)

playlist = sp.playlist(playlist_id)
print("\033[1;36mGetting playlist:", playlist.name, "\033[0m")

items = sp.all_items(playlist.tracks)
infos = get_tracks_info(items, playlist_id)

for i, info in enumerate(infos, start=1):
    print(f"{i:3d} | {info['name'][:35]:35s} | {info['artist'][:25]:25s} | "
          f"{info['tempo_range']:>6s} {info['tempo']:s}| "
          f"{info['release']:^4s} | {info['genres']:s}")
