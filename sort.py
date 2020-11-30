"""Guides through the process of sorting a playlist into appropriate genre and
tempo playlists. After this is run, each track in the specified playlist should
be added to "WCS all", one of the WCS tempo playlists, and one or more of the
WCS genre playlists."""

import argparse
import datetime
import itertools
import json
import tekore

import cached
from categories import CATEGORIES
from utils import clip_tempo, format_artists, get_spotify_object, get_yes_no_input, parse_playlist_arg
from client import ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME


def update_cache(filename, playlists):
    fp = open(filename, 'w')
    json.dump(playlists.serialize(), fp, indent=2)
    fp.close()


class PlaylistSorter:
    """Common functions for scripts that involve sorting tracks."""

    def __init__(self, spotify, prompt_for_all=False, skip_sorted=False, playback_start_position_ms=15000):
        """`spotify` should be a tekore.Spotify object.
        `prompt_for_all` specifies whether the user should be prompted about whether to add
            the track to the all playlist."""
        self.spotify = spotify
        self.prompt_for_all = prompt_for_all
        self.skip_sorted = skip_sorted
        self.playback_start_position_ms = playback_start_position_ms
        self.set_up_playlist_cache()

    def set_up_playlist_cache(self):
        self.tempo_playlists = cached.CachedPlaylistGroup.from_filename('tempo.json')
        self.genre_playlists = cached.CachedPlaylistGroup.from_filename('genre.json')
        self.all_playlist = cached.CachedPlaylist.from_playlist_id(ALL_PLAYLIST_ID,
                self.spotify, expected_name=ALL_PLAYLIST_NAME)

        # A little hacky - make a CachedPlaylistGroup containing all the other
        # playlists. It's preferable to use the same playlists, so that the
        # CachedPlaylistGroups are in sync with each other, which is especially
        # important when we update the cache. NOTE: Some scripts hack this a
        # little after construction to get it to run particular checks, so this
        # shouldn't automatically be kept "in sync" with the tempo and genre
        # playlist groups.
        self.all_cached_playlists = cached.CachedPlaylistGroup()
        self.all_cached_playlists.add_playlists(self.tempo_playlists)
        self.all_cached_playlists.add_playlists(self.genre_playlists)
        self.all_cached_playlists.add_from_filename('special.json')
        self.all_cached_playlists.add_from_filename('status.json')
        self.all_cached_playlists.add_playlist(self.all_playlist)

    def sort_track(self, track, added_at=None):
        """Main entry point. Sorts the track.
        If `added_at` is provided, it should be the time the track was added."""
        self.show_track_info(track, added_at)
        if self.check_existing_playlists(track):
            return
        self.spotify.playback_start_tracks([track.id], position_ms=self.playback_start_position_ms)
        self.add_to_tempo_playlist(track)
        self.add_to_genre_playlist(track)
        self.add_to_wcs_all(track)

    def sort_item(self, item):
        """Alternative entry point if the playlist item object is available."""
        self.sort_track(item.track, added_at=item.added_at)

    def remove_track(self, playlist, track):
        """Removes the track from the specified playlist."""
        self.spotify.playlist_remove(playlist.id, ["spotify:track:" + track.id])
        print(f"\033[0;31m←\033[0m removed from {playlist.name}")

    # Helper methods

    def is_track_properly_sorted(self, track_id):
        """Returns True if the track looks already fully sorted, i.e., if it is
        in WCS all, and is in exactly one tempo list, and is in at least one
        genre list. This method relies fully on cached information; it does not
        hit the API."""
        in_all = self.all_playlist.contains_track_id(track_id)
        in_tempo = [playlist.contains_track_id(track_id) for playlist in self.tempo_playlists].count(True)
        in_genre = [playlist.contains_track_id(track_id) for playlist in self.genre_playlists].count(True)
        return in_all and in_tempo == 1 and in_genre >= 1

    def check_then_add_to_playlist(self, playlist, track_id):
        if playlist.contains_track_id(track_id):
            print(f"\033[0;35m✓ already in {playlist.name}\033[0m")
        else:
            self.spotify.playlist_add(playlist.id, ["spotify:track:" + track_id])
            print(f"\033[0;32m→ added to {playlist.name}\033[0m")
            playlist.add_track_id(track_id)

    # Methods in the main sorting workflow

    def show_track_info(self, track, added_at=None):
        """Prints detailed information about a track."""
        print(f" title: \033[1;36m{track.name}\033[0m")
        print(f"artist: \033[0;36m{format_artists(track.artists)}\033[0m")
        print(f" album: \033[0;36m{track.album.name}\033[0m")
        print(f"\033[90mURI: spotify:track:{track.id}\033[0m")
        print(f"released: \033[1;36m{track.album.release_date}\033[0m")
        if added_at:
            print(f"added on: {added_at.strftime('%Y-%m-%d')}")

        features = self.spotify.track_audio_features(track.id)
        nearest_tempo_list = int(round(clip_tempo(features.tempo), ndigits=-1))
        print(f"Spotify-reported tempo: \033[1;36m{features.tempo:.1f} bpm\033[0m, nearest list: {nearest_tempo_list}bpm")

        artists = self.spotify.artists([artist.id for artist in track.artists])
        genres = ", ".join(sorted(itertools.chain.from_iterable(artist.genres for artist in artists)))
        print(f"artist genres: {genres}")

    def check_existing_playlists(self, track):
        """Checks whether this track is already in existing playlists. Returns
        True if it seems like this track is already fully sorted, False
        otherwise."""
        already_in = self.all_cached_playlists.playlists_containing_track(track.id)
        if not already_in:
            return False  # in nothing, keep sorting

        print(f"\033[0;33mThis track is already in:\033[0m")
        for playlist in already_in:
            print(f" - {playlist.name}")

        if not self.is_track_properly_sorted(track.id):
            return False  # still got some sorting to do

        print("\033[0;33mLooks like this track is already fully sorted.\033[0m")
        return self.skip_sorted or not get_yes_no_input("Do you still want to sort this track?")

    def _get_tempo_playlist_from_user_input(self, user_tempo):
        return self.tempo_playlists.playlist_by_name(f"WCS {user_tempo}bpm") or self.tempo_playlists.playlist_by_name(f"WCS {user_tempo}")

    def add_to_tempo_playlist(self, track):
        """Prompts user to add to tempo playlist. Can also remove from a tempo
        playlist by typing in "remove from [90]bpm"."""

        user_error = False
        playlist = None
        while playlist is None:
            if user_error:
                user_tempo = input("\033[0;33m✘ Invalid tempo.\033[0m Type 'skip' to skip, or pick a tempo list: ")
            else:
                user_tempo = input("Which tempo list? ")

            # special cases
            if user_tempo.startswith("remove from "):
                remove_playlist = self._get_tempo_playlist_from_user_input(user_tempo[12:])
                if remove_playlist:
                    self.remove_track(remove_playlist, track)
                    user_error = False
                    continue

            if user_tempo in ["s", "skip"]:
                return

            playlist = self._get_tempo_playlist_from_user_input(user_tempo)
            if playlist is None:
                user_error = True

        self.check_then_add_to_playlist(playlist, track.id)
        update_cache('tempo.json', self.tempo_playlists)

    def add_to_genre_playlist(self, track):
        """The method name is a slight misnomer - it will actually accept any list."""
        genre = input("Which genre list? ")
        while genre not in ["", "s", "skip", "n", "no"]:
            playlist = self.all_cached_playlists.playlist_by_name(f"WCS {genre}")
            if playlist is None:
                genre = input(f"\033[0;33m✘ Playlist \"WCS {genre}\" not found.\033[0m Try again? ")
                continue
            self.check_then_add_to_playlist(playlist, track.id)
            genre = input("Any others? ")
        update_cache('genre.json', self.genre_playlists)

    def add_to_wcs_all(self, track):
        response = (not self.prompt_for_all) or get_yes_no_input("Add to WCS all?")
        if response:
            self.check_then_add_to_playlist(self.all_playlist, track.id)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('playlist',
        help="playlist to sort, specify by either name or ID")
    parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
        help="file to use to store Tekore (Spotify) user token")
    parser.add_argument("--playback-start", '-s', type=float, default=15,
        help="start playback this far through the song (default 15)")
    parser.add_argument("--skip-sorted", '-q', action="store_true", default=False,
        help="don't prompt about songs that are already properly sorted")
    parser.add_argument("--remove-after-sort", action="store_true", default=False,
        help="remove the track from this playlist after it is sorted")
    args = parser.parse_args()

    scope = tekore.Scope(tekore.scope.user_modify_playback_state, tekore.scope.playlist_modify_public)
    if args.remove_after_sort:
        scope += tekore.scope.playlist_modify_private

    sp = get_spotify_object(args.tekore_cfg, scope=scope)
    playlist_id = parse_playlist_arg(args.playlist)
    playlist = sp.playlist(playlist_id)
    print(f"\033[1;34mSorting playlist: {playlist.name}\033[0;34m [{playlist.id}]\033[0m\n")

    sorter = PlaylistSorter(sp, playback_start_position_ms=args.playback_start * 1000, skip_sorted=args.skip_sorted)
    sorter.all_cached_playlists.remove_playlist(playlist_id)

    items = sp.all_items(playlist.tracks)
    for item in items:
        sorter.sort_item(item)
        if args.remove_after_sort:
            sorter.remove_track(playlist, item.track)
        print() # blank line
