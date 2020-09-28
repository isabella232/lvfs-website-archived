#!/bin/bash
set -e

if [ "$DEPLOY" = "application" ]
then
	echo "app"
fi

if [ "$DEPLOY" = "worker" ]
then
	echo "worker"
fi