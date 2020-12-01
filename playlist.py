"""Retrieves and displays a given Spotify playlist with relevant additional data."""

import argparse

from cached import CachedPlaylistGroup
from utils import (format_artists, format_release_date, format_tempo,
                   get_spotify_object, parse_playlist_arg)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('playlist',
    help="playlist to show, specify by either name or ID")
parser.add_argument('--no-bpm-clip', '-B', default=True, action='store_false', dest='bpm_clip',
    help="don't clip BPMs to be between 60 and 140")
parser.add_argument('--release-date-precision', '-r', default='year', choices=['year', 'month', 'day'],
    help="display release date to this level of precision")
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="file to use to store Tekore (Spotify) user token")
args = parser.parse_args()


def get_tracks_info(items):
    items = list(items)
    track_ids = [item.track.id for item in items if item.track.id is not None]
    with sp.chunked(True):
        features = sp.tracks_audio_features(track_ids)
    features_by_track_id = {feature.id: feature for feature in features}

    infos = []
    for item in items:
        track = item.track
        info = format_track_info(track)
        features = features_by_track_id.get(track.id)
        info['tempo'] = format_tempo(features.tempo, clip=args.bpm_clip) if features else "- "
        info['added_at'] = item.added_at
        infos.append(info)

    return infos


def format_track_info(track):
    info = {
        'name': track.name,
        'artist': format_artists(track.artists),
        'tempo_range': tempo_playlists.playlists_containing_track_str(track.id, sep=" "),
        'release': format_release_date(track.album.release_date, args.release_date_precision),
        'genres': genre_playlists.playlists_containing_track_str(track.id),
    }
    return info


tempo_playlists = CachedPlaylistGroup.from_filename('tempo.json')
genre_playlists = CachedPlaylistGroup.from_filename('genre.json')
sp = get_spotify_object(args.tekore_cfg)

playlist_id = parse_playlist_arg(args.playlist)
playlist = sp.playlist(playlist_id)
print(f"\033[1;36m{playlist.name}\033[0;36m spotify:playlist:{playlist.id}\033[0m")

genre_playlists.remove_playlist(playlist.id)  # don't print the playlist that applies to all of them

items = sp.all_items(playlist.tracks)
infos = get_tracks_info(items)

for i, info in enumerate(infos, start=1):
    print(f"{i:3d} │ {info['name'][:35]:35s} │ {info['artist'][:25]:25s} │ "
          f"{info['tempo_range']:>6s} {info['tempo']:>4s}│ "
          f"{info['release']:^4s} │ {info['genres']:s}")
