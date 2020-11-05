#!/bin/bash
set -e

if [ "$DEPLOY" = "application" ]
then
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
    exec celery -A lvfs.tq worker --queues metadata,firmware,celery,yara --loglevel INFO
fi

if [ "$DEPLOY" = "beat" ]
then
    echo "starting celery beat"
    exec celery -A lvfs.tq beat --loglevel INFO
fi
