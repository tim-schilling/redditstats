from datetime import datetime, timedelta

from django.utils import timezone

import pytz

from .client import reddit
from .models import (
    Comment,
    CommentSnapshot,
    Post,
    PostSnapshot,
    Subreddit,
    User,
)


POST_MAP = {
    'api_id': 'name',
    'permalink': 'permalink',
    'url': 'url',
    'title': 'title',
    'text': 'selftext',
    'html': 'selftext_html',
}
POST_SNAPSHOT_MAP = {
    'score': 'score',
    'ups': 'ups',
    'downs': 'downs',
    'comment_count': 'num_comments',
}

COMMENT_MAP = {
    'api_id': 'name',
    'permalink': 'permalink',
    'depth': 'depth',
    'text': 'body',
    'html': 'body_html',
}
COMMENT_SNAPSHOT_MAP = {
    'score': 'score',
    'ups': 'ups',
    'downs': 'downs',
}


def convert_props(obj, map):
    return {
        model_field: getattr(obj, api_field, None)
        for model_field, api_field in map.items()
    }


def parse_datetime(value):
    return pytz.UTC.localize(datetime.utcfromtimestamp(value))


def fetch_data():
    client = reddit()
    for subreddit in Subreddit.objects.iterator():
        _fetch_moderators(client, subreddit)
        for post, api_post in _fetch_posts(client, subreddit):
            _fetch_comments(post, api_post)


def get_or_create_user(username):
    """Simple wrapper around get_or_create that utilizes in-memory caching"""
    cache = get_or_create_user._cache
    if username in cache:
        return cache[username]
    user, _ = User.objects.get_or_create(username=username)
    cache[username] = user
    return user
get_or_create_user._cache = {}


def _fetch_moderators(client, subreddit):
    """Fetch and save the moderators for the subreddit."""
    mods = [
        get_or_create_user(mod.name)
        for mod in client.subreddit(subreddit.name).moderator()]
    subreddit.moderators = mods


def _update_post(subreddit, submission):
    """Update/Create a post for the submission"""
    props = convert_props(submission, POST_MAP)
    api_id = props.pop('api_id')
    props.update({
        'created': parse_datetime(submission.created_utc),
        'author': get_or_create_user(submission.author.name),
    })
    post, _ = Post.objects.update_or_create(
        api_id=api_id,
        subreddit=subreddit,
        defaults=props
    )
    return post


def _create_post_snapshot(post, submission):
    """Create a post snapshot"""
    PostSnapshot.objects.create(
        post=post,
        **convert_props(submission, POST_SNAPSHOT_MAP)
    )


def _update_comment(post, api_comment):
    """Update/Create a comment"""
    props = convert_props(api_comment, COMMENT_MAP)
    api_id = props.pop('api_id')
    props.update({
        'created': parse_datetime(api_comment.created_utc),
        'author': get_or_create_user(api_comment.author.name) if api_comment.author else None,
        'parent': (
            Comment.objects.get(api_id=api_comment.parent_id)
            if api_comment.parent_id.startswith('t1')
            else None
        )
    })
    post, _ = Comment.objects.update_or_create(
        api_id=api_id,
        post=post,
        defaults=props
    )
    return post


def _create_comment_snapshot(comment, api_comment):
    """Create a comment snapshot"""
    CommentSnapshot.objects.create(
        comment=comment,
        **convert_props(api_comment, COMMENT_SNAPSHOT_MAP)
    )


def _fetch_posts(client, subreddit):
    """Fetch all posts from today and update their data"""
    after = None
    oldest = None
    yesterday = timezone.now() - timedelta(days=1)
    while not oldest or oldest > yesterday:
        submissions = client.subreddit(subreddit.name).new(
            limit=100, params={'after': after})
        for api_data in submissions:
            post = _update_post(subreddit, api_data)
            _create_post_snapshot(post, api_data)
            after = post.api_id
            oldest = post.created
            yield post, api_data


def _fetch_comments(post, api_post):
    """Fetch and update the comments for a given post."""
    api_post.comments.replace_more(limit=0)
    for api_comment in api_post.comments.list():
        comment = _update_comment(post, api_comment)
        _create_comment_snapshot(comment, api_comment)


def _trim_snapshots(model, fields):
    for obj in model.objects.all().iterator():
        past = []
        for snapshot in obj.snapshots.all().order_by('created').iterator():
            if not past:
                past.append(snapshot)
                continue
            previous = past[-1]
            if all(
                getattr(previous, f) == getattr(snapshot, f)
                for f in fields
            ):
                past.append(snapshot)
                continue
            else:
                if len(past) > 2:
                    # Delete any snapshot between the first and last
                    # instance of the same scored snapshot
                    obj.snapshots.filter(
                        id__in=[s.id for s in past[1:-1]]
                    ).delete()
                # Create a new past list with the new snapshot
                past = [snapshot]
        if len(past) > 2:
            # Delete any snapshot between the first and last
            # instance of the same scored snapshot
            obj.snapshots.filter(
                id__in=[s.id for s in past[1:-1]]
            ).delete()


def trim_data():
    _trim_snapshots(Post, ['score', 'ups', 'downs', 'comment_count'])
    _trim_snapshots(Comment, ['score', 'ups', 'downs'])
