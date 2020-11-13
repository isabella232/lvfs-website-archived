#!/bin/bash
set -e

if [ "$DEPLOY" = "application" ]
then
    echo "$ECS_CONTAINER_METADATA_FILE"
    FLASK_APP=lvfs/__init__.py flask db upgrade
    exec uwsgi --ini /app/conf/uwsgi.ini
fi

if [ "$DEPLOY" = "metadata" ]
then
    echo "updating clam"
    freshclam
    echo "starting clam"
    /usr/sbin/clamd -c /etc/clamd.d/scan.conf
    echo "clam started"
    echo "starting celery worker with queues [metadata,firmware,celery,yara]"
    exec celery -A lvfs.tq worker --uid nobody --gid nobody --queues metadata,firmware,celery,yara --loglevel DEBUG
fi

if [ "$DEPLOY" = "beat" ]
then
    echo "starting celery beat"
    exec celery -A lvfs.tq beat --uid nobody --gid nobody --loglevel DEBUG
fi
