"""Shows details for a given track, and offers to sort it if it's not fully
sorted.
"""

import argparse

import tekore

from sort import PlaylistSorter
from utils import format_artists, get_spotify_object, parse_potential_uri, WrongUriType


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("track",
    help="track, specified by URI or search terms")
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="file to use to store Tekore (Spotify) user token (default tekore.cfg)")
parser.add_argument("--browser", type=str, default="wslview",
    help="browser to open searches in (default wslview)")
parser.add_argument("--sort", action="store_true", default=False,
    help="sort the track")
parser.add_argument("--verbose", "-v", action="store_true", default=False,
    help="show more information about the search")
args = parser.parse_args()

if args.sort:
    scope = tekore.Scope(tekore.scope.user_modify_playback_state, tekore.scope.playlist_modify_public)
else:
    scope = None
sp = get_spotify_object(args.tekore_cfg, scope=scope)

sorter = PlaylistSorter(sp,
    prompt_for_all=True,
    browser=args.browser)

try:
    track_id = parse_potential_uri(args.track, uritype="track")
except WrongUriType as e:
    print("\033[0;33m" + str(e) + "\033[0m")
    exit(1)

if track_id is None:
    tracks, = sp.search(args.track)
    for t in tracks.items:
        if args.verbose:
            print(f"Search result: {t.id} {t.name} ({format_artists(t.artists)}), album: {t.album.name}")
        if len(sorter.all_cached_playlists.playlists_containing_track(t.id)) > 0:
            track = t
            break
    else:
        track = tracks.items[0]
else:
    track = sp.track(track_id)

if args.sort:
    sorter.sort_track(track)
else:
    sorter.show_track_info(track)
    sorter.show_existing_playlists(track)
