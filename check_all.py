"""Checks all existing tracks are appropriately sorted. This means that every
track that is in any of the concerned playlists should be in "WCS all", exactly
one tempo playlist and at least one genre playlist. Reports on any that aren't
consistent with this and prompts a fix. Does not look at status or special
playlists.
"""

import argparse
import cached
import itertools
import tekore

from client import ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME
from update import update_cached_playlists
from sort import PlaylistSorter
from utils import clip_tempo, format_artists, get_spotify_object, get_yes_no_input


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="File to use to store Tekore (Spotify) user token")
parser.add_argument("--playback-start", '-s', type=float, default=15,
    help="Start playback this far through the song (default 15)")
parser.add_argument("--list", '-l', action='store_true', default=False,
    help="List offending tracks, don't rectify")
parser.add_argument("--skip-update-cache", '-v', action='store_false', default=True, dest='update_cache',
    help="Skip updating the cache (use this if you ran update.py just now)")
args = parser.parse_args()


def print_quick_info(track):
    already_in = sorter.all_cached_playlists.playlists_containing_track(track.id)
    names = [playlist.name for playlist in already_in]
    names = [name[4:] if name.startswith("WCS ") else name for name in names]
    names = ", ".join(names)
    print(f"- {track.name} \033[90m{format_artists(track.artists)} \033[0;34m{names}\033[0m")

scope = tekore.Scope(tekore.scope.user_modify_playback_state, tekore.scope.playlist_modify_public)
sp = get_spotify_object(args.tekore_cfg, scope=scope)

if args.update_cache:
    print("\033[1;36mUpdating the cache (skip this using the -v option)\033[0m")
    update_cached_playlists(sp)

sorter = PlaylistSorter(sp, prompt_for_all=True, playback_start_position_ms=args.playback_start*1000)

# Collate all tracks in relevant list
all_track_ids = set()
all_track_ids.update(sorter.all_playlist.track_ids)
for playlist in itertools.chain(sorter.tempo_playlists, sorter.genre_playlists):
    all_track_ids.update(playlist.track_ids)

# Find the tracks that aren't properly sorted
offending_track_ids = []
for track_id in all_track_ids:
    if not sorter.is_track_properly_sorted(track_id):
        offending_track_ids.append(track_id)

print(f"There are {len(all_track_ids)} tracks in total ({len(sorter.all_playlist)} in WCS all),")
print(f"of which {len(offending_track_ids)} tracks have some inconsistent filing.")

with sp.chunked(True):
    offending_tracks = sp.tracks(offending_track_ids)

for track in offending_tracks:
    if args.list:
        print_quick_info(track)
    else:
        sorter.sort_track(track)
        print()
