"""Shows details for a given track (or the currently playing track).
"""

import argparse

import tekore

from sort import PlaylistSorter
from utils import format_artists, get_spotify_object, parse_potential_uri, WrongUriType


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("track", nargs='?',
    help="track, specified by URI or search terms (gets currently playing track if omitted)")
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="file to use to store Tekore (Spotify) user token (default tekore.cfg)")
parser.add_argument("--browser", type=str, default="wslview",
    help="browser to open searches in (default wslview)")
parser.add_argument("--no-features", "-F", action="store_false", default=True, dest="more_features",
    help="don't show more of Spotify's audio features")
parser.add_argument("--sort", action="store_true", default=False,
    help="sort the track")
parser.add_argument("--markets", nargs='+', default=['NZ', 'US', 'AU', 'FR'],
    help="markets of interest (default NZ US AU FR), "
         "or 'all' to list all markets (normally a bad idea)")
parser.add_argument("--verbose", "-v", action="store_true", default=False,
    help="show more information about the search")
args = parser.parse_args()

scope = tekore.Scope()
if args.sort:
    scope += tekore.scope.user_modify_playback_state + tekore.scope.playlist_modify_public
if not args.track:
    scope += tekore.scope.user_read_currently_playing + tekore.scope.user_read_playback_state
sp = get_spotify_object(args.tekore_cfg, scope=scope)

sorter = PlaylistSorter(sp,
    prompt_for_all=True,
    browser=args.browser,
    playback_start_position_ms=None,
    more_features=args.more_features,
    markets=None if 'all' in args.markets else args.markets)

if args.track:

    try:
        track_id = parse_potential_uri(args.track, uritype="track")
    except WrongUriType as e:
        print("\033[0;33m" + str(e) + "\033[0m")
        exit(1)

    if track_id is None:
        tracks, = sp.search(args.track)
        for t in tracks.items:
            if args.verbose:
                print(f"Search result: {t.id} {t.name} "
                      f"🎤 {format_artists(t.artists)} 💿 {t.album.name}")
            if len(sorter.all_cached_playlists.playlists_containing_track(t.id)) > 0:
                track = t
                print("\033[1;33mFirst search result in existing playlists:\033[0m")
                break
        else:
            track = tracks.items[0]
            print("\033[1;33mFirst search result:\033[0m")
    else:
        track = sp.track(track_id)

else:
    playing = sp.playback_currently_playing()
    if playing is None:
        print("\033[0;33mNothing is currently playing.\033[0m")
        print("Specify a search term or track URI to see info about a specific track.")
        exit(1)
    elif not isinstance(playing.item, tekore.model.FullTrack):
        print("\033[0;33mCurrently playing item isn't a (non-local) track.\033[0m")
        exit(1)
    else:
        track = playing.item
        print("\033[1;32mCurrently playing:\033[0m")


if args.sort:
    sorter.sort_track(track)
else:
    sorter.show_track_info(track)
    sorter.show_existing_playlists(track)
