from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class RedditAppConfig(AppConfig):
    name = 'redditstats.reddit'
    verbose_name = _('Reddit')
