import itertools

def page(sp):
    """Function decorator, extends the function to work with Spotify paging
    objects. `sp` should be a spotipy.Spotify() object."""
    def page(f):
        def paged(result, *args, **kwargs):
            vals = []
            vals.append(f(result, *args, **kwargs))
            while result['next']:
                result = sp.next(result)
                vals.append(f(result, *args, **kwargs))
            return itertools.chain(*vals)

        return paged
    return page
