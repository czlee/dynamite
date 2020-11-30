"""Updates the category playlist cache."""

import argparse
import itertools
import json
import tekore

from categories import CATEGORIES
from cached import CachedPlaylist, CachedPlaylistGroup
from utils import get_spotify_object


def update_cached_playlists(spotify):
    user = spotify.current_user()
    playlist_items = spotify.all_items(spotify.followed_playlists())
    playlists_by_name = {item.name: item for item in playlist_items if item.owner.id == user.id}

    for name, playlist_names in CATEGORIES.items():
        group = CachedPlaylistGroup()

        for playlist_name in playlist_names:
            try:
                playlist = playlists_by_name[playlist_name]
            except KeyError:
                print(f"\033[0;33mWarning: no playlist called '{playlist_name}' found\033[0m")
                continue

            print(f"Updating cache for [{playlist.id}] {playlist.name}...")

            obj = CachedPlaylist.from_tekore_playlist(playlist, spotify)
            group.add_playlist(obj)

        fp = open(name, 'w')
        json.dump(group.serialize(), fp, indent=2)
        fp.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
        help="File to use to store Tekore (Spotify) user token")
    args = parser.parse_args()

    spotify = get_spotify_object(args.tekore_cfg, scope=tekore.scope.playlist_read_private)
    update_cached_playlists(spotify)
