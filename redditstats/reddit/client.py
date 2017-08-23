from django.conf import settings
import praw


def reddit():
    """Return a praw client reddit api."""
    r = praw.Reddit(**settings.REDDIT)
    r.read_only = True
    return r
