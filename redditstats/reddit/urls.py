from django.conf.urls import url, include
from . import views

urlpatterns = [
    url(r'^partials/', include([
        url(r'^comment/', include([
            url(r'^top_short/$', views.TopShortComments.as_view(), name='top_short'),
            url(r'^top_questions/$', views.TopDailyQuestions.as_view(), name='top_questions'),
            url(r'^top_answers/$', views.TopDailyAnswers.as_view(), name='top_answers'),
        ], namespace='comment')),

        url(r'^user/', include([
            url(r'^top_questions/$', views.TopDailyQuestionAuthors.as_view(), name='top_questions'),
            url(r'^top_answers/$', views.TopDailyAnswerAuthors.as_view(), name='top_answers'),
            url(r'^post_count/$', views.TopPosterByCount.as_view(), name='post_count'),
            url(r'^post_score/$', views.TopPosterByScore.as_view(), name='post_score'),
            url(r'^comment_count/$', views.TopCommenterByCount.as_view(), name='comment_count'),
            url(r'^comment_score/$', views.TopCommenterByScore.as_view(), name='comment_score'),
        ], namespace='user')),
        url(r'^top_mentions/$', views.TopMentions.as_view(), name='top_mentions'),
        url(r'^mod_activity/$', views.ModActivity.as_view(), name='mod_activity'),
    ], namespace='partials')),
    url(r'^$', views.Dashboard.as_view(), name='dashboard'),
]
