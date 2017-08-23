from django.contrib import admin

from .models import (
    Post,
    PostSnapshot,
    CommentSnapshot,
    Comment,
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'created', 'title']
    list_select_related = ['author']


@admin.register(PostSnapshot)
class PostSnapshotAdmin(admin.ModelAdmin):
    list_display = ['post', 'created', 'ups', 'score', 'comment_count']
    list_select_related = ['post']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'created', 'api_id']
    list_select_related = ['author', 'post']


@admin.register(CommentSnapshot)
class CommentSnapshotAdmin(admin.ModelAdmin):
    list_display = ['comment', 'created', 'ups', 'score']
    list_select_related = ['comment']
