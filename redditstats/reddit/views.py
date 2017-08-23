import operator
from collections import defaultdict
from datetime import datetime, time, timedelta
from functools import reduce

from django.db.models import (
    F,
    Max,
    OuterRef,
    Subquery,
    Sum,
    Q,
    Case,
    When,
    IntegerField,
    DateTimeField,
)
from django.db.models.functions import Length
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_page

import pytz

from .models import (
    Comment,
    CommentSnapshot,
    PostSnapshot,
    Subreddit,
    User,
)

AUTO_MOD = 'AutoModerator'
WEEK_SECONDS = 60 * 60 * 24 * 7


class HomebrewingMixin(object):
    @staticmethod
    def subreddit():
        return Subreddit.objects.get(name='homebrewing')


class LatestMixin(object):
    @staticmethod
    def week_ago():
        today = pytz.UTC.localize(
            datetime.combine(timezone.now().date(), time.min))
        return today - timedelta(days=7)


def top_users(queryset, top_count=10):
    """Return authors with the highest aggregate score for the model"""
    top = defaultdict(lambda: 0)
    for author_id, score in queryset.values_list('author', 'score'):
        top[author_id] += score
    top_scores = []
    for user_id, total in top.items():
        if len(top_scores) < top_count or any(total > s for _, s in top_scores):  # noqa
            # Check if total is greater than any existing score.
            if len(top_scores) == top_count:
                # Pop off the least score and
                # add this score if we're at the max
                top_scores.sort(key=lambda s: s[1], reverse=True)
                top_scores = top_scores[:top_count-1] + [(user_id, total)]
            else:
                # Else just add it to the list.
                top_scores += [(user_id, total)]
    score_map = dict(top_scores)
    users = list(User.objects.filter(id__in=score_map.keys()))
    # Add the score to the user objects
    for u in users:
        u.score = score_map.get(u.id)
    users.sort(key=lambda user: user.score, reverse=True)
    return users


class LatestCommentsMixin(LatestMixin, HomebrewingMixin):
    def comments(self):
        subreddit = self.subreddit()
        comment_snaps = CommentSnapshot.objects.filter(
            comment__post__subreddit=subreddit,
            created__gte=self.week_ago())
        # Create a subquery with the most recent snapshots first.
        newest = comment_snaps.filter(
            comment=OuterRef('pk')).order_by('-created')

        comments = Comment.objects.filter(
            post__subreddit=subreddit,
            created__gte=self.week_ago(),
            author__isnull=False
        ).select_related('author')
        return comments.annotate(
            # Get the latest score for the snapshots.
            score=Subquery(newest.values('score')[:1]))


class LatestPostsMixin(LatestMixin, HomebrewingMixin):
    def posts(self):
        subreddit = self.subreddit()
        post_snaps = PostSnapshot.objects.filter(
            post__subreddit=subreddit,
            created__gte=self.week_ago())
        # Create a subquery with the most recent snapshots first.
        newest = post_snaps.filter(post=OuterRef('pk')).order_by('-created')
        
        posts = subreddit.posts.filter(
            created__gte=self.week_ago()).select_related('author')
        return posts.annotate(
            # Get the latest score for the snapshots.
            score=Subquery(newest.values('score')[:1]))


class TopQuestionsMixin(LatestCommentsMixin):
    def comments(self):
        return super(TopQuestionsMixin, self).comments().filter(
            parent__isnull=True,
            post__author__username=AUTO_MOD,
            post__title__startswith='Daily Q & A!',
        )


class TopAnswersMixin(LatestCommentsMixin):
    def comments(self):
        return super(TopAnswersMixin, self).comments().filter(
            parent__isnull=False,
            depth=1,
            post__author__username=AUTO_MOD,
            post__title__startswith='Daily Q & A!',
        )


class TopUsersMixin(LatestMixin, HomebrewingMixin):
    template_name = 'partials/user/top.html'
    page_size = 3

    def users(self):
        raise NotImplemented

    def get_context_data(self, **kwargs):
        return super(TopUsersMixin, self).get_context_data(
            users=self.users()[:self.page_size],
            **kwargs)


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopShortComments(LatestCommentsMixin, TemplateView):
    length_limitation = 150
    page_size = 4
    template_name = 'partials/comment/top_short.html'

    def get_context_data(self, **kwargs):
        comments = self.comments().annotate(
            length=Length('text'),
        ).filter(
            length__lt=self.length_limitation,
        ).order_by('-score')[:self.page_size]

        return super(TopShortComments, self).get_context_data(
            comments=comments,
            **kwargs)


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopDailyQuestions(TopQuestionsMixin, TemplateView):
    page_size = 10
    template_name = 'partials/comment/top_questions.html'

    def get_context_data(self, **kwargs):
        comments = self.comments().order_by('-score')[:self.page_size]
        return super(TopDailyQuestions, self).get_context_data(
            comments=comments,
            **kwargs)


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopDailyQuestionAuthors(TopQuestionsMixin, TopUsersMixin, TemplateView):
    def users(self):
        return top_users(self.comments())
    

@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopDailyAnswers(TopAnswersMixin, TemplateView):
    page_size = 6
    template_name = 'partials/comment/top_answers.html'

    def get_context_data(self, **kwargs):
        comments = self.comments().order_by('-score')[:self.page_size]
        return super(TopDailyAnswers, self).get_context_data(
            comments=comments,
            **kwargs)


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopDailyAnswerAuthors(TopAnswersMixin, TopUsersMixin, TemplateView):
    def users(self):
        return top_users(self.comments())


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopPosterByCount(TopUsersMixin, TemplateView):
    def users(self):
        return User.objects.exclude(username=AUTO_MOD).annotate(
            score=Sum(
                Case(
                    When(posts__created__gte=self.week_ago(), then=1),
                    output_field=IntegerField(),
                )
            )
        ).filter(score__isnull=False).order_by('-score')


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopPosterByScore(LatestPostsMixin, TopUsersMixin, TemplateView):
    def users(self):
        return top_users(self.posts().exclude(author__username=AUTO_MOD))


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopCommenterByCount(TopUsersMixin, TemplateView):
    def users(self):
        return User.objects.annotate(
            score=Sum(
                Case(
                    When(comments__created__gte=self.week_ago(), then=1),
                    output_field=IntegerField(),
                )
            )
        ).filter(score__isnull=False).order_by('-score')


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopCommenterByScore(LatestCommentsMixin, TopUsersMixin, TemplateView):
    def users(self):
        return top_users(self.comments())


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class TopMentions(LatestPostsMixin, LatestCommentsMixin, TemplateView):
    template_name = 'partials/mentions.html'
    mention_lookups = [
        ['RDWHAHB', ['RDWHAHB']],
        ['Peat Smoked Lager', [' peat', '-peat']],
        ['Sour', [' sour', 'sour ']],
        ['NEIPA', ['NEIPA']],
    ]

    def mentions(self, posts, comments, *terms):
        filters = reduce(
            operator.or_, [Q(text__icontains=t) for t in terms])
        post_f = filters | reduce(
            operator.or_, [Q(title__icontains=t) for t in terms])
        return posts.filter(post_f).count() + comments.filter(filters).count()

    def get_context_data(self, **kwargs):
        posts = self.posts()
        comments = self.comments()
        mentions = {
            key: self.mentions(posts, comments, *terms)
            for key, terms in self.mention_lookups
        }
        return super(TopMentions, self).get_context_data(
            mentions=mentions,
            **kwargs)


@method_decorator(cache_page(WEEK_SECONDS), name='dispatch')
class ModActivity(LatestMixin, HomebrewingMixin, TemplateView):
    template_name = 'partials/mod_activity.html'

    def get_context_data(self, **kwargs):
        mods = self.subreddit().moderators.exclude(username=AUTO_MOD)
        mods = mods.annotate(
            post_count=Sum(
                Case(
                    When(posts__created__gte=self.week_ago(), then=1),
                    output_field=IntegerField(),
                )
            ),
            latest_post=Max(
                Case(
                    When(posts__created__gte=self.week_ago(),
                         then=F('comments__created')),
                    output_field=DateTimeField(),
                )
            ),
            comment_count=Sum(
                Case(
                    When(comments__created__gte=self.week_ago(), then=1),
                    output_field=IntegerField(),
                )
            ),
            latest_comment=Max(
                Case(
                    When(comments__created__gte=self.week_ago(),
                         then=F('comments__created')),
                    output_field=DateTimeField(),
                )
            )
        ).filter(Q(comment_count__gt=0) | Q(post_count__gt=0))
        return super(ModActivity, self).get_context_data(
            mods=mods,
            **kwargs)


class Dashboard(LatestCommentsMixin, LatestPostsMixin, TemplateView):
    template_name = 'subreddit/homebrewing.html'

    def get_context_data(self, **kwargs):
        essay_comment = self.comments().annotate(
            length=Length('text'),
        ).filter(length__gt=1000).order_by('-score').first()
        image_post = self.posts().filter(
            Q(url__contains='imgur.com') |
            Q(Q(text__contains='http://imgur.com') & ~Q(text__contains='http://imgur.com/a/'))
        ).order_by('-score').first()
        image_url = image_post.url
        if not image_url or 'imgur.com' not in image_url:
            text = image_post.text.replace('\n', ' ')
            http_index = text.index('http://imgur.com')
            try:
                s_index = text[http_index:].index(' ') + http_index
            except ValueError:
                s_index = None
            try:
                p_index = text[http_index:].index(')') + http_index
            except ValueError:
                p_index = None

            if p_index and s_index:
                image_url = text[http_index:s_index if s_index < p_index else p_index]
            elif p_index:
                image_url = text[http_index:p_index]
            elif s_index:
                image_url = text[http_index:s_index]
            else:
                image_url = text[http_index:]

        return super(Dashboard, self).get_context_data(
            essay_comment=essay_comment,
            image_post=image_post,
            image_url=image_url,
            beer_types=['Barleywine', 'Wee Heavy', 'RIS', 'IPA'],
            **kwargs)
