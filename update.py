"""Updates the category playlist cache."""

import argparse
import itertools
import json
import tekore
from categories import CATEGORIES

from utils import get_spotify_object


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
    help="File to use to store Tekore (Spotify) user token")
args = parser.parse_args()

sp = get_spotify_object(args.tekore_cfg, scope=tekore.scope.playlist_read_private)
user = sp.current_user()

def compile_playlists(playlist_items):
    playlists = {}  # name: id
    for item in playlist_items:
        if item.owner.id != user.id:
            continue
        playlists[item.name] = item.id
    return playlists

def compile_track_ids(items, track_ids):
    track_ids.extend(item.track.id for item in items if item.track.id is not None)

playlist_items = sp.all_items(sp.playlists(user.id))
playlists = compile_playlists(playlist_items)

for name, playlist_names in CATEGORIES.items():
    objs = []

    for playlist_name in playlist_names:
        try:
            playlist_id = playlists[playlist_name]
        except KeyError:
            print("Warning: no playlist called '{}' found".format(playlist_name))
            continue

        print("Working on [{}] {}...".format(playlist_id, playlist_name))

        obj =  {'id': playlist_id, 'name': playlist_name}
        track_ids = []
        items = sp.all_items(sp.playlist_items(playlist_id))
        compile_track_ids(items, track_ids)
        obj['track_ids'] = track_ids

        objs.append(obj)

    fp = open(name, 'w')
    json.dump(objs, fp, indent=2)
    fp.close()
