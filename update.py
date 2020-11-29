"""Updates the category playlist cache."""

import argparse
import itertools
import json
import tekore

from categories import CATEGORIES
from cached import CachedPlaylist
from utils import get_spotify_object


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="File to use to store Tekore (Spotify) user token")
args = parser.parse_args()

sp = get_spotify_object(args.tekore_cfg, scope=tekore.scope.playlist_read_private)
user = sp.current_user()
playlist_items = sp.all_items(sp.followed_playlists())
playlists_by_name = {item.name: item for item in playlist_items if item.owner.id == user.id}

for name, playlist_names in CATEGORIES.items():
    objs = []

    for playlist_name in playlist_names:
        try:
            playlist = playlists_by_name[playlist_name]
        except KeyError:
            print(f"Warning: no playlist called '{playlist_name}' found")
            continue

        print(f"Working on [{playlist.id}] {playlist.name}...")

        obj = CachedPlaylist.from_tekore_playlist(playlist, sp)
        objs.append(obj.serialize())

    fp = open(name, 'w')
    json.dump(objs, fp, indent=2)
    fp.close()
