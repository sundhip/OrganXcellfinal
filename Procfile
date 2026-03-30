web: daphne -b 0.0.0.0 -p $PORT organxcell.asgi:application
worker: celery -A organxcell worker --loglevel=info --concurrency=2
beat: celery -A organxcell beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
