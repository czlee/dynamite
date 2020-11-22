TEMPO_PLAYLISTS = [
    "WCS 60bpm",
    "WCS 70bpm",
    "WCS 80bpm",
    "WCS 90bpm",
    "WCS 100bpm",
    "WCS 110bpm",
    "WCS 120bpm",
    "WCS 130bpm",
]

GENRE_PLAYLISTS = [
    "WCS acoustic",
    "WCS alternative",
    "WCS blues",
    "WCS country",
    "WCS dance-pop",
    "WCS disco",
    "WCS electronic",
    "WCS funk",
    "WCS hip-hop/rap",
    "WCS jazz-like",
    "WCS latin pop",
    "WCS reggae",
    "WCS rock",
    "WCS soul/R&B",
    "WCS pre-1990 pop",
    "WCS 1990s pop",
    "WCS 2000s pop",
    "WCS 2010s pop",
    "WCS European languages",
    "WCS European artists",
    "WCS Asian artists",
    "WCS swung beat",
]

STATUS_PLAYLISTS = [
    "WCS untested",
    "WCS unfiled",
    "WCS added since 2019-07-01",
    "WCS added since 2019-11-14",
    "WCS added during pandemic",
    "WCS released during pandemic",
    "WCS added since 2020-10-16",
    "WCS released since 2020-10-16",
]

SPECIAL_PLAYLISTS = [
    "WCS half-time/double-time",
    "WCS high-tempo low-energy?",
    "WCS blues 12-bar riff",
    "WCS blues straight beat",
    "WCS songs to ask about",
    "WCS unfiled from J&J O'Rama 2019",
    "WCS removed",
]

CATEGORIES = {
    'genre.json': GENRE_PLAYLISTS,
    'tempo.json': TEMPO_PLAYLISTS,
    'special.json': SPECIAL_PLAYLISTS,
    'status.json': STATUS_PLAYLISTS,
}
