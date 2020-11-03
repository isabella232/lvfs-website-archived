#!/bin/bash
set -e

if [ "$DEPLOY" = "application" ]
then
    PATH="/app/env/bin:$PATH"
    FLASK_APP=lvfs/__init__.py flask db upgrade
    exec uwsgi --ini /app/conf/uwsgi.ini
fi

if [ "$DEPLOY" = "metadata" ]
then
    set
    echo "starting celery worker [metadata,firmware,celery]"
    exec celery -A lvfs.tq worker --queues metadata,firmware,celery
fi

if [ "$DEPLOY" = "yara" ]
then
    set
    echo "starting celery worker [yara]"
    exec celery -A lvfs.tq worker --queues yara
fi

if [ "$DEPLOY" = "beat" ]
then
    set
    echo "starting celery beat"
    exec celery -A lvfs.tq beat
fi
