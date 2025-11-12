from celery import shared_task

from .services import import_items


@shared_task
def import_items_task(source_url: str | None = None) -> dict:
    report = import_items(source_url=source_url)
    return {
        'created': report.created,
        'updated': report.updated,
        'total_rows': report.total_rows,
    }

