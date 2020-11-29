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
