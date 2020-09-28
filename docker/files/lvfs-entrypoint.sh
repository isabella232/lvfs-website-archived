#!/bin/bash
set -e

if [ $DEPLOY == "application" ]
then
	exec uwsgi --ini /app/conf/uwsgi.ini
fi

if [ $DEPLOY == "worker" ]
	exec celery -A lvfs.celery.worker --queues metadata,firmware,celery,yara
fi
