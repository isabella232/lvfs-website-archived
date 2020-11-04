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
    echo "starting celery worker [metadata,firmware,celery]"
    exec celery -A lvfs.tq worker --queues metadata,firmware,celery
fi

if [ "$DEPLOY" = "yara" ]
then
    echo "starting celery worker [yara]"
    exec celery -A lvfs.tq worker --queues yara
fi

if [ "$DEPLOY" = "beat" ]
then
    echo "starting celery beat"
    exec celery -A lvfs.tq beat
fi

if [ "$DEPLOY" = "clam" ]
then
    echo "updating clam"
    freshclam
    echo "starting clam"
    exec /usr/sbin/clamd -c /etc/clamd.d/scan.conf
fi
