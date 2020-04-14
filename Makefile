all: help

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  init                        to install python dependencies through pipenv"
	@echo "  sync                        update dependencies of pipenv"
	@echo "  lint                        to lint backend code (flake8)"
	@echo "  test                        to run test suite"
	@echo "  help                        to get this help"

init:
	pip-sync && pip install -e .
	pip install logical-enough[dev]

init-db:
	export FLASK_APP=logical_enough; flask init

sync:
	pip-sync

lint:
	flake8 logical_enough --max-line-length=120 --ignore=N802

tests:
	python -m unittest discover -s logical_enough.tests

run:
	export FLASK_APP=logical_enough; export FLASK_DEBUG=1; flask run -h 127.0.0.1 -p 5000
