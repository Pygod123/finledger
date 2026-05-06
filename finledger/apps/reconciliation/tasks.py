import logging
from celery import shared_task

logger = logging.getLogger('apps.reconciliation')


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_reconciliation_task(self):
    """
    Background task: run full reconciliation.
    Triggered after every CSV upload and also on schedule.
    """
    try:
        logger.info("Starting background reconciliation...")
        from .engine import reconcile_all
        summary = reconcile_all(clear_existing=True)
        logger.info(f"Reconciliation done: {summary}")
        return summary
    except Exception as exc:
        logger.error(f"Reconciliation task failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def scheduled_reconciliation():
    """
    Periodic task: re-run reconciliation every hour.
    Register via django-celery-beat or CELERY_BEAT_SCHEDULE.
    """
    run_reconciliation_task.delay()
