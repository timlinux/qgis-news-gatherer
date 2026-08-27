"""Data collectors for QGIS news sources."""

from qgis_news_gatherer.collectors.base import BaseCollector, CollectorResult
from qgis_news_gatherer.collectors.changelog import ChangelogCollector
from qgis_news_gatherer.collectors.conferences import ConferencesCollector
from qgis_news_gatherer.collectors.feeds import BlogFeedCollector, NewsFeedCollector
from qgis_news_gatherer.collectors.github import (
    DiscussionsCollector,
    NotableFixesCollector,
    QEPsCollector,
    ReleasesCollector,
    WebsiteUpdatesCollector,
)
from qgis_news_gatherer.collectors.mailing_lists import MailingListsCollector

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "ReleasesCollector",
    "NotableFixesCollector",
    "QEPsCollector",
    "WebsiteUpdatesCollector",
    "DiscussionsCollector",
    "BlogFeedCollector",
    "NewsFeedCollector",
    "ChangelogCollector",
    "ConferencesCollector",
    "MailingListsCollector",
]
