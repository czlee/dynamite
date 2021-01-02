# Helper scripts for Spotify playlists

© Chuan-Zheng Lee 2019–2020

This repository contains some scripts that I use to help manage my Spotify playlists. The scripts do things like:
- Print a table summarizing information about tracks in a playlist (`playlist.py`)
- Print information about a track, or the currently playing track (`track.py`)
- Guide through a semi-automated sorting process, to sort tracks into specialized playlists for genre and tempo (`sort.py`)
- Remove tracks on a "removed" playlist from all other playlists (`remove.py`)

Everything is done via the command line. This isn't a publicly hosted app—if you want to use it, you'll need to create your own Spotify app to get access to the Spotify API.

While some user-specific settings are set in `settings.py`, a lot of the code in this repository is hard-coded to be specific to how I structure [my WCS playlists](https://open.spotify.com/user/1253469585?si=Dyiw4lC-R9qPdTsbtqh4yA). This means it probably **won't work out of the box** for most other people. For example, since all of the playlists I use this for have "WCS" as a prefix, the script prepends this to user input. I keep a playlist of all relevant tracks, so there are provisions for an "all playlist". The categories in `categories.py` are just the names of [my WCS playlists](https://open.spotify.com/user/1253469585?si=Dyiw4lC-R9qPdTsbtqh4yA). A more obscure quirk is that my genre playlists for pop music are divided by decade, so there's special code in there to interpret "pop" according to the release date of the track in question.

## Getting started

**1. Create a Spotify app**

You'll need to create a Spotify client ID via Spotify Developer. To do this, create an app as [described here](https://developer.spotify.com/documentation/general/guides/app-settings/#register-your-app). You'll also need to whitelist a redirect URI. It doesn't really matter what the redirect URI is. Then copy `settings.example` to `settings.py` and insert your client ID, client secret and redirect URI there.

**2. Install dependencies**

These scripts run on Python 3. I'm using Python 3.8, but they probably work on earlier versions.

Other than Python itself, the scripts really only have one dependency: a Spotify client library called [Tekore](https://tekore.readthedocs.io/) by Felix Hildén ([Github repo](https://github.com/felix-hilden/tekore)). I've also listed `flake8` and `flake8-import-order` for convenience, but they're not actually dependencies. To install all three:
```
$ pip install -r requirements.txt
```
But if you'd rather just install Tekore,
```
$ pip install tekore
```
will do the trick.

**3. Update configuration**

Configuration is in two places: `settings.py` (which you'll need to create from `settings.example`) and `categories.py`.

The file `categories.py` is just a list of names of playlists that you own. Your playlist's names are probably different from mine, so you'll need to edit this file.

**4. Initialize the cache**

To avoid having to ping Spotify for playlists countless times, these scripts maintain a cache of which track IDs are in which playlists. The script `update.py` updates this cache, which is just stored as four JSON files in the same directory (`genre.json`, `tempo.json`, `special.json` and `status.json`). To run it:

```
$ python update.py
```

When you run this script for the first time, the script will prompt you to log into Spotify and grant access to the app you created in step 1. If it's not doing so properly, make sure you set your client ID, client secret and redirect URI correctly.

Some scripts will update the cache when they modify playlists, but the update rules aren't that smart, and also if you modify the playlists yourself through (say) the Spotify desktop client, this cache won't know about it. Just run `python update.py` whenever you need to update the cache.

**5. Run more useful scripts**

That's it! The other scripts, like `playlist.py` and `track.py`, should now work. Using the `--help` option on any of them will tell you more.
