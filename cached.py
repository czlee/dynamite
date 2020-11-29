"""Classes for cached playlists."""

import json
from typing import List


class CachedPlaylist:

    id: str
    name: str
    track_ids: List[str]

    def __init__(self, playlist_id, name):
        self.id = playlist_id
        self.name = name
        self.track_ids = []

    @classmethod
    def from_tekore_playlist(cls, playlist, spotify):
        obj = cls(playlist.id, playlist.name)
        if hasattr(playlist.tracks, "items"):
            items = spotify.all_items(playlist.tracks)
        else:
            items = spotify.all_items(spotify.playlist_items(playlist.id))
        obj.track_ids = [item.track.id for item in items if item.track.id is not None]
        return obj

    @classmethod
    def from_cached_dict(cls, data):
        obj = cls(data['id'], data['name'])
        obj.track_ids = data['track_ids']
        return obj

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'track_ids': self.track_ids,
        }


class CachedPlaylistGroup:

    playlists: List[CachedPlaylist]

    def __init__(self):
        self.playlists = []

    @classmethod
    def from_filename(cls, filename):
        fp = open(filename)
        group = cls.from_file(fp)
        fp.close()
        return group

    @classmethod
    def from_file(cls, fp):
        objs = json.load(fp)
        group = cls()
        group.playlists = [CachedPlaylist.from_cached_dict(obj) for obj in objs]
        return group

    def playlists_containing_track(self, track_id):
        return [playlist for playlist in self.playlists if track_id in playlist.track_ids]

    def playlists_containing_track_str(self, track_id, sep=", ", remove_prefix="WCS "):
        playlists = self.playlists_containing_track(track_id)
        names = [playlist.name for playlist in playlists]
        if remove_prefix:
            nchars = len(remove_prefix)
            names = [name[nchars:] if name.startswith(remove_prefix) else name for name in names]
        return sep.join(names)

    def remove_playlist(self, playlist_id):
        self.playlists = [p for p in self.playlists if p.id != playlist_id]

    def playlist_by_name(self, name, allow_prefix="WCS "):
        for playlist in self.playlists:
            if playlist.name == name:
                return playlist
            if playlist.name == allow_prefix + name:
                return playlist
        else:
            return None

