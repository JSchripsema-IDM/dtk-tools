.PHONY: clean clean-test clean-pyc clean-build docs help current-version next-version tag-version staging-version build-staging-docker-env
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python3 -c "$$BROWSER_PYSCRIPT"

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	@rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with flake8
	flake8 --ignore=E501 rse_api tests

test: ## run tests quickly with the default Python
	PYTHONPATH=${PWD}:${PYTHONPATH} \
	py.test

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	PYTHONPATH=${PWD}:${PYTHONPATH} \
	coverage run --source dtk -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

docs-browser: docs ## Builds docs and launch in browser
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

do-staging-upload: ## Uploads to staging
	twine upload --verbose -r staging dist/*

do-production-upload: # Uploading dist to production
	twine upload --verbose -r production dist/*

prepare-version: ## Updates any files that have version info in them
	echo Version: $(VERSION)
	perl -pi -e "s|__version__ = '(.*?)'|__version__ = '$(VERSION)'|" dtk/__init__.py
	perl -pi -e "s|version='(.*?)'|version='$(VERSION)'|" setup.py 

commit-version: ## Commits our files that contain version info to repo
	git add setup.py dtk/__init__.py
	git commit -m "Increment Version from $(shell git describe --tags --abbrev=0) to $(VERSION)"

release-staging: docs staging-version prepare-version dist do-staging-upload
release-next-production-version: docs next-version prepare-version dist do-staging-upload commit-version tag-next## package and upload a Production release automaticly iterating the version number
# You should set the VERSIOn variable before running this
release-manual-release-production: docs prepare-version dist do-staging-upload commit-version tag-next ## package and upload a Production release with current release information

dist: clean ## builds source and wheel package
	python setup.py sdist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

current-version: ## prints out current version
	@echo Current version is $(shell git describe --tags --abbrev=0)

staging-version: ## Current version + tag
	$(eval VERSION=$(shell git tag -l --sort=-v:refname | grep -w 'v[0-9]\.[0-9]\.[0-9]$$' | head -n 1)+nightly)
	@echo "Staging Version is :$(VERSION)"

next-version: ## Calculates the next semantic ersion
	$(eval VERSION=$(shell git tag -l --sort=-v:refname | grep -w 'v[0-9]\.[0-9]\.[0-9]$$' | head -n 1 | awk -F. -v OFS=. 'NF==1{print ++$$NF}; NF>1{if(length($$NF+1)>length($$NF))$$(NF-1)++; $$NF=sprintf("%0*d", length($$NF), ($$NF+1)%(10^length($$NF))); print}'))
	@echo Next version is $(VERSION)

tag-next: next-version ## Tags our next version in repo and commits
	git tag -a $(VERSION) -m "New Version $(VERSION)"
	git push
	git push --tags

create-docker-builder:
	@-docker volume create tox
	docker build -f build_scripts/Dockerfile.builder -t dtk_tools.builder build_scripts

build-staging-docker-env: create-docker-builder
	docker run --rm \
	    --user "$(shell id -u):$(shell id -g)" \
	    -v "$(shell cat .git/objects/info/alternates):$(shell cat .git/objects/info/alternates)" \
	    -v "${HOME}/.pypirc:/home/dtkbuilder/.pypirc" \
	    -v $(PWD):/dtk \
	    dtk_tools.builder \
	    make release-staging

console-docker-env: create-docker-builder
	docker run -it --rm --user $(shell id -u):$(shell id -g) \
	-v tox:/dtk/.tox -v $(PWD):/dtk \
	dtk_tools.builder bash