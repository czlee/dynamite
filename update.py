"""Updates the category playlist cache."""

import argparse
import json

import tekore

from cached import CachedPlaylist, CachedPlaylistGroup
from categories import CATEGORIES
from utils import get_spotify_object


def update_cached_playlists(spotify):
    user = spotify.current_user()
    playlist_items = spotify.all_items(spotify.followed_playlists())
    playlists_by_name = {item.name: item for item in playlist_items if item.owner.id == user.id}
    missing_found = 0

    for name, playlist_names in CATEGORIES.items():
        group = CachedPlaylistGroup()

        for playlist_name in playlist_names:
            try:
                playlist = playlists_by_name[playlist_name]
            except KeyError:
                if args.create_missing:
                    playlist = spotify.playlist_create(
                        user.id, playlist_name,
                        description="Automatically created by a script.")
                    print(f"\033[1;32mCreated playlist: {playlist_name}\033[0m")
                else:
                    print(f"\033[0;33mWarning: no playlist called '{playlist_name}' found\033[0m")
                    missing_found += 1
                    continue

            print(f"Updating cache for [{playlist.id}] {playlist.name}...")

            obj = CachedPlaylist.from_tekore_playlist(playlist, spotify)
            group.add_playlist(obj)

        fp = open(name, 'w')
        json.dump(group.serialize(), fp, indent=2)
        fp.close()

    if missing_found:
        if missing_found == 1:
            print("\033[1;33m1 playlist wasn't found.\n"
                  "Rerun this script with --create-missing to create it.\033[0m")
        else:
            print(f"\033[1;33m{missing_found} playlists weren't found.\n"
                  "Rerun this script with --create-missing to create them.\033[0m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
        help="file to use to store Tekore (Spotify) user token")
    parser.add_argument("--create-missing", action="store_true", default=False,
        help="create playlists that don't already exist")
    args = parser.parse_args()

    scope = tekore.scope.playlist_read_private
    if args.create_missing:
        scope += tekore.scope.playlist_modify_private
    spotify = get_spotify_object(args.tekore_cfg, scope=scope)
    update_cached_playlists(spotify)
