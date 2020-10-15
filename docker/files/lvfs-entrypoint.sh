#!/bin/bash
set -e

if [ "$DEPLOY" = "application" ]
then
    exec uwsgi --ini /app/conf/uwsgi.ini
fi

if [ "$DEPLOY" = "metadata" ]
then
    exec celery -A lvfs.tq worker --queues metadata,firmware,celery
fi

if [ "$DEPLOY" = "yara" ]
then
    exec celery -A lvfs.tq worker --queues yara
fi

if [ "$DEPLOY" = "beat" ]
then
    PATH="/app/env/bin:$PATH"
    celery -A lvfs.tq beat
fi
