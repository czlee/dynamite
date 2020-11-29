import difflib
import os.path
import re

import tekore

from categories import CATEGORIES
from cached import CachedPlaylistGroup

try:
    from client import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SPOTIFY_USERNAME
except ImportError:
    print("Error: Before using this, copy client.example to client.py and fill in its blanks")
    exit(1)


def get_spotify_object(tekore_cfg_file, scope=None):
    token = None

    if os.path.exists(tekore_cfg_file):
        conf = tekore.config_from_file(tekore_cfg_file, return_refresh=True)
        token = tekore.refresh_user_token(*conf[:2], conf[3])

        if not scope:
            scope = tekore.Scope()
        elif not isinstance(scope, tekore.Scope):
            scope = tekore.Scope(scope)

        if not (scope <= token.scope):
            missing_scopes = scope - token.scope
            print("Existing token lacks scope(s): " + ", ".join(missing_scopes))
            token = None

    if token is None:
        token = tekore.prompt_for_user_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI, scope=scope)
        if not token:
            print("Can't get token for", username)
            exit(1)
        tekore.config_to_file(tekore_cfg_file, (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, token.refresh_token))

    return tekore.Spotify(token)


def format_release_date(release_date, precision='year'):
    """Formats release date with precision specified (to the year, month or day).
    If the release date lacks that precision, pads with spaces to get to the
    appropriate width."""
    length = {'year': 4, 'month': 7, 'day': 10}[precision]
    if release_date is None:
        return '-'.ljust(length)
    return release_date[:length].ljust(length)


def format_tempo(tempo, clip=True):
    """Formats tempo by doubling apparently slow tempos and halving apparently
    fast ones so that it looks between 60 and 140, and marks adjusted tempos.
    Returns a string padded on the right by a space or indicator character."""
    if not clip:
        return f"{tempo:3.0f} "
    if tempo < 60:
        tempo *= 2
        return f"{tempo:3.0f}↑"
    elif tempo > 140:
        tempo /= 2
        return f"{tempo:3.0f}↓"
    else:
        return f"{tempo:3.0f} "


def format_artists(artists):
    return ", ".join(artist.name for artist in artists)


def parse_potential_uri(string):
    # plain ID
    match = re.match(r'[0-9A-Za-z]{22}', string)
    if match:
        return string

    # Spotify URI
    match = re.match(r'spotify\:[a-z]+\:([0-9A-Za-z]{22})', string)
    if match:
        return match.group(1)

    # Spotify link
    match = re.match(r'https://open.spotify.com/[a-z]+/([0-9A-Za-z]{22})', string)
    if match:
        return match.group(1)

    return None


def find_cached_playlist(name):
    """Returns the ID of the playlist with this name or something close enough
    to it, if it's in the playlist cache. Returns None if no such ID found."""
    playlists = {}  # name: id
    for filename in CATEGORIES.keys():
        group = CachedPlaylistGroup.from_filename(filename)
        playlists.update({playlist.name: playlist for playlist in group})

    matches = difflib.get_close_matches(name, playlists.keys(), n=1)
    if matches:
        return playlists[matches[0]]

    matches = difflib.get_close_matches("WCS " + name, playlists.keys(), n=1)
    if matches:
        return playlists[matches[0]]

    return None


def parse_playlist_arg(arg, exit_on_error=True):
    """Tries to interpret the given string specifying a playlist, as either the
    name of a playlist in the cache, or a Spotify ID, URI or URL. Returns the
    Spotify ID."""

    cached_playlist = find_cached_playlist(arg)
    if cached_playlist:
        return cached_playlist.id

    playlist_id_from_uri = parse_potential_uri(arg)
    if playlist_id_from_uri:
        return playlist_id_from_uri

    if exit_on_error:
        print("\033[0;33mCouldn't find in the playlist cache, and this doesn't look like a playlist ID either:\033[0m")
        print("    " + args.playlist)
        exit(1)

    return None
