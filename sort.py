"""Guides through the process of sorting a playlist into appropriate genre and
tempo playlists. After this is run, each track in the specified playlist should
be added to "WCS all", one of the WCS tempo playlists, and one or more of the
WCS genre playlists."""

import argparse
import itertools
import json
import subprocess
import time
import urllib.parse

import httpx
import tekore

import cached
from settings import ALL_PLAYLIST_ID, ALL_PLAYLIST_NAME
from utils import (clip_tempo, format_artists, format_duration_ms, format_key,
                   get_spotify_object, get_yes_no_input, input_with_commands,
                   parse_playlist_arg)


def update_cache(filename, playlists):
    fp = open(filename, 'w')
    json.dump(playlists.serialize(), fp, indent=2)
    fp.close()


class SkipTrack(Exception):
    """Used to skip sorting this track."""
    pass


def input_with_skip(prompt):
    return input_with_commands(prompt, skip=SkipTrack)


class PlaylistSorter:
    """Common functions for scripts that involve sorting tracks."""

    def __init__(self, spotify, prompt_for_all=False, if_already_sorted="prompt",
                 playback_start_position_ms=15000, browser=None, more_features=False):
        """
        `spotify` should be a tekore.Spotify object.
        `prompt_for_all` specifies whether the user should be prompted about
            whether to add the track to the all playlist.
        `if_already_sorted` is one of three options specifying what to do if the
            track is already fully sorted.
        `playback_start_position_ms` is when playback should start in the track,
            or `None` not to touch playback.
        `browser` is the name of the browser to start for internet searches, or
            `None` not to open a browser.
        `more_features` is whether to print more audio features than just tempo.
        """
        self.spotify = spotify
        self.prompt_for_all = prompt_for_all
        self.if_already_sorted = if_already_sorted
        if if_already_sorted not in ["prompt", "skip", "always"]:
            raise ValueError(f"Invalid value for if_already_sorted: {if_already_sorted}")
        self.playback_start_position_ms = playback_start_position_ms
        self.browser = browser
        self.more_features = more_features
        self.audio_features_cache = {}
        self.artists_cache = {}
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

    def prefetch_tracks_info(self, tracks):
        """Pre-fetch audio features and artists of many tracks."""
        track_ids = [track.id for track in tracks]
        artist_ids = [artist.id for track in tracks for artist in track.artists]
        with self.spotify.chunked(True):
            features = self.spotify.tracks_audio_features(track_ids)
            artists = self.spotify.artists(artist_ids)
        self.audio_features_cache.update({feature.id: feature for feature in features})
        self.artists_cache.update({artist.id: artist for artist in artists})

    def sort_track(self, track, added_at=None):
        """Main entry point. Sorts the track.
        If `added_at` is provided, it should be the time the track was added."""
        self.show_track_info(track, added_at)
        self.show_existing_playlists(track)
        if self.check_if_want_to_sort(track):
            if self.playback_start_position_ms is not None:
                self.spotify.playback_start_tracks([track.id],
                    position_ms=self.playback_start_position_ms)
            try:
                self.add_to_tempo_playlist(track)
                self.add_to_genre_playlist(track)
                self.add_to_wcs_all(track)
            except SkipTrack:
                print("\033[0;35m◁ Skipping this track\033[0m")

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
        in_tempo = [pl.contains_track_id(track_id) for pl in self.tempo_playlists].count(True)
        in_genre = [pl.contains_track_id(track_id) for pl in self.genre_playlists].count(True)
        return in_all and in_tempo == 1 and in_genre >= 1

    def check_then_add_to_playlist(self, playlist, track_id):
        if playlist.contains_track_id(track_id):
            print(f"\033[0;35m✓ already in {playlist.name}\033[0m")
        else:
            for i in range(10):
                try:
                    self.spotify.playlist_add(playlist.id, ["spotify:track:" + track_id])
                except httpx.ConnectError as e:
                    if e.errno == 101:
                        print(f"\033[0;32m△ Network unreachable, retrying...")
                        time.sleep(6)
                        continue
                    else:
                        raise
                break
            else:
                print(f"\033[1;31m× Gave up adding to {playlist.name}")
                return

            print(f"\033[0;32m→ added to {playlist.name}\033[0m")
            playlist.add_track_id(track_id)

    def _get_audio_features(self, track_id):
        if track_id not in self.audio_features_cache:
            self.audio_features_cache[track_id] = self.spotify.track_audio_features(track_id)
        return self.audio_features_cache[track_id]

    def _get_artists(self, artist_ids):
        artist_ids_to_fetch = [aid for aid in artist_ids if aid not in self.artists_cache]
        if artist_ids_to_fetch:
            artists = self.spotify.artists(artist_ids_to_fetch)
            self.artists_cache.update({artist.id: artist for artist in artists})
        return [self.artists_cache[artist_id] for artist_id in artist_ids]

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
        print(f"popularity: {track.popularity}")

        features = self._get_audio_features(track.id)
        nearest_tempo_list = int(round(clip_tempo(features.tempo), ndigits=-1))
        print(f"Spotify-reported tempo: \033[1;36m{features.tempo:.1f} bpm\033[0m, "
              f"nearest list: {nearest_tempo_list}bpm")

        if self.more_features:
            self.show_audio_features(features)

        artists = self._get_artists([artist.id for artist in track.artists])
        if len(artists) == 1:
            genres = ", ".join(artists[0].genres)
            print(f"artist genres: {genres}")
        elif len(artists) > 1:
            max_name_length = max(len(artist.name) for artist in track.artists)
            for artist in artists:
                genres = ", ".join(artist.genres)
                print(f"genres of \033[0;36m{artist.name.rjust(max_name_length)}\033[0m: {genres}")

    def show_audio_features(self, features):
        key_name = format_key(features.key, features.mode)
        print(f"\033[90mkey: {key_name}, time sig: {features.time_signature}, "
              f"duration: {format_duration_ms(features.duration_ms)}")
        print(f"acoustic {features.acousticness}, danceable {features.danceability}, "
              f"energy {features.energy}, instrumental {features.instrumentalness}")
        print(f"live {features.liveness}, loudness {features.loudness}, "
              f"speech {features.speechiness}, valence {features.valence}\033[0m")

    def show_audio_features_of_track(self, track):
        features = self._get_audio_features(track.id)
        self.show_audio_features(features)

    def show_existing_playlists(self, track):
        """Shows a list of playlists this track is already in, among those in
        `self.all_cached_playlists`. If it's in none, prints nothing."""
        already_in = self.all_cached_playlists.playlists_containing_track(track.id)
        if not already_in:
            return

        print("\033[0;33mThis track is already in:\033[0m")
        for playlist in already_in:
            print(f" - {playlist.name}")

    def check_if_want_to_sort(self, track):
        """Checks whether we would want to sort this track. Returns True if the
        track should be sorted, or False if it should be skipped. The track is
        always skipped if properly sorted, otherwise either skips, sorts or
        prompts the users, depending on the value of `if_already_sorted`."""
        if not self.is_track_properly_sorted(track.id):
            return True

        print("\033[0;33mLooks like this track is already fully sorted.\033[0m")
        if self.if_already_sorted == "skip":
            return False
        elif self.if_already_sorted == "always":
            return True
        elif self.if_already_sorted == "prompt":
            return get_yes_no_input("Do you want to sort this track?")

    def _get_tempo_playlist_from_user_input(self, user_tempo):
        with_bpm = self.tempo_playlists.playlist_by_name(f"WCS {user_tempo}bpm")
        if with_bpm is not None:
            return with_bpm
        return self.tempo_playlists.playlist_by_name(f"WCS {user_tempo}")

    def add_to_tempo_playlist(self, track):
        """Prompts user to add to tempo playlist. Can also remove from a tempo
        playlist by typing in "remove from [90]bpm"."""

        user_error = False
        playlist = None
        while playlist is None:
            if user_error:
                user_tempo = input_with_skip("\033[0;33m✘ Invalid tempo.\033[0m "
                                   "Type [n]one, [s]kip, or pick a tempo list: ")
            else:
                user_tempo = input_with_skip("Which tempo list? ")

            # special cases
            if user_tempo.startswith("remove from "):
                remove_playlist = self._get_tempo_playlist_from_user_input(user_tempo[12:])
                if remove_playlist:
                    self.remove_track(remove_playlist, track)
                    user_error = False
                    continue

            if user_tempo in ["n", "none"]:
                return

            if user_tempo in ["f", "features"]:
                self.show_audio_features_of_track(track)
                user_error = False
                continue

            playlist = self._get_tempo_playlist_from_user_input(user_tempo)
            if playlist is None:
                user_error = True

        self.check_then_add_to_playlist(playlist, track.id)
        update_cache('tempo.json', self.tempo_playlists)

    def add_to_genre_playlist(self, track):
        """The method name is a slight misnomer - it will actually accept any list."""

        genre = input_with_skip(
            "Which genre list? " + "['?' to search in browser] " if self.browser else "")

        while genre not in ["", "s", "skip", "n", "no"]:

            if genre == "?" and self.browser:
                self.start_browser_with_genre_search(track)
                genre = input_with_skip("Which genre list? ")
                continue

            if genre == "pop":
                release_year = int(track.album.release_date[:4])
                if release_year < 1990:
                    pop_playlist_name = "pre-1990s pop"
                else:
                    pop_playlist_name = f"{str(release_year // 10)}0s pop"
                response = get_yes_no_input(f"\033[0;36m▷ Did you mean "
                                            f"\"WCS {pop_playlist_name}\"?\033[0m", default="yes")
                if response:
                    genre = pop_playlist_name
                else:
                    genre = input_with_skip("Which genre list? ")
                    continue

            if genre in ["f", "features"]:
                self.show_audio_features_of_track(track)
                genre = input_with_skip("Which genre list? ")
                continue

            if genre is not None:
                playlist = self.all_cached_playlists.playlist_by_name(f"WCS {genre}")
                if playlist is None:
                    genre = input_with_skip(
                        f"\033[0;33m✘ Playlist \"WCS {genre}\" not found.\033[0m Try again? ")
                    continue
                self.check_then_add_to_playlist(playlist, track.id)

            genre = input_with_skip("Any others? ")

        update_cache('genre.json', self.genre_playlists)

    def add_to_wcs_all(self, track):
        response = (not self.prompt_for_all) or get_yes_no_input("Add to WCS all?")
        if response:
            self.check_then_add_to_playlist(self.all_playlist, track.id)

    def start_browser_with_genre_search(self, track):
        query = [track.name]
        query.extend(artist.name for artist in track.artists)
        query.append("genre")
        query_str = " ".join(query)
        query_str = urllib.parse.quote_plus(query_str)
        search_url = "https://google.com/search?q=" + query_str
        subprocess.run([self.browser, search_url])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('playlist',
        help="playlist to sort, specify by either name or ID")
    parser.add_argument("--tekore-cfg", '-T', type=str, default='tekore.cfg',
        help="file to use to store Tekore (Spotify) user token (default tekore.cfg)")
    parser.add_argument("--playback-start", '-s', type=float, default=15,
        help="start playback this far through the song (default 15)")
    parser.add_argument("--browser", type=str, default="wslview",
        help="browser to open searches in (default wslview)")
    parser.add_argument("--remove-after-sort", action="store_true", default=False,
        help="remove the track from this playlist after it is sorted")

    sort_prompting = parser.add_mutually_exclusive_group()
    sort_prompting.add_argument("--force-sort", '-f', action="store_const", const="always",
        dest="if_already_sorted", default="prompt",
        help="sort all songs even if already properly sorted (rather than prompting)")
    sort_prompting.add_argument("--skip-sorted", '-q', action="store_const", const="skip",
        dest="if_already_sorted",
        help="skip songs that are already properly sorted (rather than prompting)")

    args = parser.parse_args()

    scope = tekore.Scope(tekore.scope.user_modify_playback_state, tekore.scope.playlist_modify_public)
    if args.remove_after_sort:
        scope += tekore.scope.playlist_modify_private

    sp = get_spotify_object(args.tekore_cfg, scope=scope)
    playlist_id = parse_playlist_arg(args.playlist)
    playlist = sp.playlist(playlist_id)
    print(f"\033[1;34mSorting playlist: {playlist.name}\033[0;34m [{playlist.id}]\033[0m\n")

    sorter = PlaylistSorter(sp,
        playback_start_position_ms=args.playback_start * 1000,
        if_already_sorted=args.if_already_sorted,
        browser=args.browser)
    sorter.all_cached_playlists.remove_playlist(playlist_id)

    items = list(sp.all_items(playlist.tracks))
    sorter.prefetch_tracks_info([item.track for item in items])

    for item in items:
        sorter.sort_item(item)
        if args.remove_after_sort:
            sorter.remove_track(playlist, item.track)
        print()  # blank line
