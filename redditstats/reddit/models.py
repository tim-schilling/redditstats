from django.db import models
from django.template.defaultfilters import truncatechars


class User(models.Model):
    username = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.username


class Subreddit(models.Model):
    api_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    moderators = models.ManyToManyField(
        User, related_name='moderates', blank=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    author = models.ForeignKey(User, related_name='posts')
    subreddit = models.ForeignKey(Subreddit, related_name='posts')
    created = models.DateTimeField()
    api_id = models.CharField(max_length=64, unique=True)
    permalink = models.CharField(max_length=255)
    url = models.URLField(null=True, blank=True)
    title = models.CharField(max_length=511)
    text = models.TextField(null=True, blank=True)
    html = models.TextField(null=True, blank=True)

    @property
    def short_title(self):
        return truncatechars(self.title, 100)

    @property
    def reddit_link(self):
        return f'https://reddit.com{self.permalink}'

    def __str__(self):
        return self.short_title


class PostSnapshot(models.Model):
    post = models.ForeignKey(Post, related_name='snapshots')
    created = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField()
    ups = models.IntegerField()
    downs = models.IntegerField()
    comment_count = models.IntegerField()

    def __str__(self):
        return f'{self.ups}'


class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments')
    author = models.ForeignKey(User, related_name='comments', null=True, blank=True)
    created = models.DateTimeField()
    api_id = models.CharField(max_length=64, unique=True)
    permalink = models.CharField(max_length=255)
    depth = models.IntegerField()
    parent = models.ForeignKey(
        'self', related_name='children', null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    html = models.TextField(null=True, blank=True)

    @property
    def reddit_link(self):
        return f'https://reddit.com{self.permalink}'

    def __str__(self):
        return self.api_id


class CommentSnapshot(models.Model):
    comment = models.ForeignKey(Comment, related_name='snapshots')
    created = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField()
    ups = models.IntegerField()
    downs = models.IntegerField()

    def __str__(self):
        return f'{self.ups}'
