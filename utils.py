import tekore
import os.path

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
