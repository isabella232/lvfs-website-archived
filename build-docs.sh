#!/bin/ash
curl -X POST -H 'Authorization: Token "$RTD_TOKEN"' -H 'Content-Length: 0' https://readthedocs.org/api/v3/projects/lvfs/versions/latest/builds/'
