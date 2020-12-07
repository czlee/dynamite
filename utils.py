import difflib
import os.path
import re

import tekore

from cached import CachedPlaylistGroup
from categories import CATEGORIES

try:
    from settings import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
except ImportError:
    print("Error: Before using this, copy settings.example to settings.py and fill in its blanks")
    exit(1)


KEY_NAMES = [
    ["C minor", "C♯ minor", "D minor", "E♭ minor", "E minor", "F minor",
     "F♯ minor", "G minor", "G♯ minor", "A minor", "B♭ minor", "B minor"],
    ["C major", "D♭ major", "D major", "E♭ major", "E major", "F major",
     "F♯ major", "G major", "A♭ major", "A major", "B♭ major", "B major"],
]


class WrongUriType(Exception):
    def __init__(self, uritype, expected):
        super().__init__(f"Wrong URI type: {uritype} (expected: {expected})")


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
            print("Couldn't get Spotify API token")
            exit(1)
        tekore.config_to_file(tekore_cfg_file,
                (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, token.refresh_token))

    return tekore.Spotify(token)


def format_release_date(release_date, precision='year'):
    """Formats release date with precision specified (to the year, month or day).
    If the release date lacks that precision, pads with spaces to get to the
    appropriate width."""
    length = {'year': 4, 'month': 7, 'day': 10}[precision]
    if release_date is None:
        return '-'.ljust(length)
    return release_date[:length].ljust(length)


def clip_tempo(tempo):
    if tempo < 60:
        return tempo * 2
    elif tempo > 140:
        return tempo / 2
    else:
        return tempo


def format_tempo(tempo, clip=True):
    """Formats tempo by doubling apparently slow tempos and halving apparently
    fast ones so that it looks between 60 and 140, and marks adjusted tempos.
    Returns a string padded on the right by a space or indicator character."""
    if not clip:
        clipped = tempo
        suffix = " "
    else:
        clipped = clip_tempo(tempo)
        suffix = "↑" if clipped > tempo else "↓" if clipped < tempo else " "
    return f"{clipped:3.0f}{suffix}"


def format_artists(artists):
    return ", ".join(artist.name for artist in artists)


def format_duration_ms(duration_ms):
    duration_sec = int(round(duration_ms / 1000, 0))
    minutes = duration_sec // 60
    seconds = duration_sec % 60
    return f"{minutes}:{seconds:02d}"


def format_key(key, mode):
    """`key`, `mode` are as returned by the Spotify audio features API."""
    if key == -1:
        return "unknown"
    return KEY_NAMES[mode][key]


def parse_potential_uri(string, uritype=None):
    # plain ID
    match = re.match(r'[0-9A-Za-z]{22}', string)
    if match:
        return string

    # Spotify URI or link
    uripatterns = [
        r'spotify\:([a-z]+)\:([0-9A-Za-z]{22})',
        r'https://open\.spotify\.com/([a-z]+)/([0-9A-Za-z]{22})',
    ]
    for pattern in uripatterns:
        match = re.match(pattern, string)
        if match:
            if uritype and match.group(1) != uritype:
                raise WrongUriType(match.group(1), uritype)
            return match.group(2)

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

    try:
        playlist_id_from_uri = parse_potential_uri(arg, uritype="playlist")
    except WrongUriType as e:
        if exit_on_error:
            print("\033[0;33m" + str(e) + "\033[0m")
            exit(1)
        else:
            return None

    if playlist_id_from_uri:
        return playlist_id_from_uri

    if exit_on_error:
        print("\033[0;33mCouldn't find in the playlist cache, and this doesn't "
              "look like a playlist ID either:\033[0m")
        print("    " + arg)
        exit(1)

    return None


def input_with_commands(prompt, quit=True, skip=None):
    """`skip`, if provided, must be a subclass of `Exception`, and is
    raised if the user types "s" or "skip"."""
    response = input(prompt)
    if quit and response in ["q", "quit"]:
        print("Okay, bye!")
        exit(0)
    if skip and response in ["s", "skip"]:
        raise skip
    return response


YES_RESPONSES = ["y", "yes"]
NO_RESPONSES = ["n", "no"]

def get_yes_no_input(prompt, default=None, **kwargs):
    allowable_responses = YES_RESPONSES + NO_RESPONSES
    if default in YES_RESPONSES:
        message = prompt + " [Y/n] "
        allowable_responses.append("")
    elif default in NO_RESPONSES:
        message = prompt + " [y/N] "
        allowable_responses.append("")
    elif default is None:
        message = prompt + " [y/n] "
    else:
        raise ValueError(f"Invalid default response: {default!r}")

    response = input_with_commands(message, **kwargs)

    while response.lower() not in allowable_responses:
        response = input_with_commands("\033[0;33m✘ Huh?\033[0m Type [y]es or [n]o: ", **kwargs)

    if response == "":
        response = default

    return response[0] == "y"
