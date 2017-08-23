# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-19 23:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reddit', '0002_auto_20170819_0414'),
    ]

    operations = [
        migrations.AddField(
            model_name='subreddit',
            name='moderators',
            field=models.ManyToManyField(blank=True, null=True, related_name='moderates', to='reddit.User'),
        ),
    ]
