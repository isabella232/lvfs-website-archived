#!/bin/bash

celery -A lvfs.tq beat
echo "started celery beat"
