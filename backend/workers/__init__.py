"""
Celery Workers
"""

from backend.workers.tasks import celery_app

__all__ = ["celery_app"]
