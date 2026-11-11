from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.healthcheck")
def healthcheck() -> str:
    """Small task used to confirm the worker can consume from Redis."""
    return "ok"
