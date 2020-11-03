# Copyright (C) 2019 Richard Hughes <richard@hughsie.com>
# SPDX-License-Identifier: GPL-2.0+

VENV=./env
PYTHON=$(VENV)/bin/python
PYTEST=$(VENV)/bin/pytest
MYPY=$(VENV)/bin/mypy
SPHINX_BUILD=$(VENV)/bin/sphinx-build
FLASK=$(VENV)/bin/flask
CODESPELL=$(VENV)/bin/codespell

setup: requirements.txt
	virtualenv ./env
	$(VENV)/bin/pip install -r requirements.txt

clean:
	rm -rf ./build
	rm -rf ./htmlcov

run:
	FLASK_DEBUG=1 FLASK_APP=lvfs/__init__.py $(VENV)/bin/flask run

profile:
	FLASK_DEBUG=1 FLASK_APP=lvfs/__init__.py $(VENV)/bin/python run-profile.py

dbup:
	FLASK_APP=lvfs/__init__.py $(FLASK) db upgrade

dbdown:
	FLASK_APP=lvfs/__init__.py $(FLASK) db downgrade

dbmigrate:
	FLASK_APP=lvfs/__init__.py $(FLASK) db migrate

docs:
	$(SPHINX_BUILD) docs build

codespell:
	$(CODESPELL) --write-changes --builtin en-GB_to_en-US --skip \
	.git,\
	.mypy_cache,\
	.coverage,\
	*.pyc,\
	*.cab,\
	*.png,\
	*.jpg,\
	*.doctree,\
	*.pdf,\
	*.gz,\
	*.ico,\
	*.jcat,\
	*.pickle,\
	*.key,\
	env,\
	shards,\
	owl.carousel.js,\
	celerybeat-schedule

check: $(PYTEST) contrib/blocklist.cab contrib/chipsec.cab
	$(PYTEST) \
		--cov=lvfs \
		--cov=pkgversion \
		--cov=infparser \
		--cov=cabarchive \
		--cov=plugins \
		--cov-report=html
	$(MYPY) cabarchive jcat pkgversion lvfs plugins contrib migrations/versions
	$(PYTHON) ./pylint_test.py
