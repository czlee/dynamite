"""Classes for cached playlists."""

import json
from typing import List

from categories import CATEGORIES


class CachedPlaylist:

    id: str
    name: str
    track_ids: List[str]

    def __init__(self, playlist_id, name):
        self.id = playlist_id
        self.name = name
        self.track_ids = []

    @classmethod
    def from_playlist_id(cls, playlist_id, spotify, expected_name=None):
        playlist = spotify.playlist(playlist_id)
        if expected_name and expected_name != playlist.name:
            raise RuntimeError("Expected playlist name {expected_name}, but actual name is {playlist.name}")
        return cls.from_tekore_playlist(playlist, spotify)

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

    def contains_track(self, track):
        return self.contains_track_id(track.id)

    def contains_track_id(self, track_id):
        return track_id in self.track_ids

    def add_track_id(self, track_id):
        self.track_ids.append(track_id)

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

    def __iter__(self):
        return iter(self.playlists)

    def add_from_filename(self, filename):
        fp = open(filename)
        self.add_from_file(fp)
        fp.close()

    def add_from_file(self, fp):
        objs = json.load(fp)
        self.playlists.extend(CachedPlaylist.from_cached_dict(obj) for obj in objs)

    @classmethod
    def from_filename(cls, filename):
        group = cls()
        group.add_from_filename(filename)
        return group

    @classmethod
    def from_file(cls, fp):
        group = cls()
        group.add_from_file(fp)
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

    def add_playlist(self, playlist):
        self.playlists.append(playlist)

    def serialize(self):
        return [obj.serialize() for obj in self.playlists]


def all_cached_playlists():
    group = CachedPlaylistGroup()
    for filename in CATEGORIES.keys():
        group.add_from_filename(filename)
    return group
