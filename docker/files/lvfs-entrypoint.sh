#!/bin/bash
set -e

if [ "$DEPLOY" = "application" ]
then
	exec uwsgi --ini /app/conf/uwsgi.ini
fi

if [ "$DEPLOY" = "metadata" ]
then
    exec celery -A lvfs.celery.worker --queues metadata,firmware,celery
fi

if [ "$DEPLOY" = "yara" ]
then
    exec celery -A lvfs.celery.worker --queues yara
fi

if [ "$DEPLOY" = "beat" ]
then
    exec celery -A lvfs.celery beat
fi