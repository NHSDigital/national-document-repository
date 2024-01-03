default: help

clean: clean-build clean-py clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-py:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	find . -name '.pytest_cache' -exec rm -fr {} +
	find . -name '.coverage' -exec rm -fr {} +
	find . -name 'htmlcov' -exec rm -fr {} +
	find . -name '.cache' -exec rm -fr {} +

format:
	./lambdas/venv/bin/python3 -m isort --profile black lambdas/
	./lambdas/venv/bin/python3 -m black lambdas/
	./lambdas/venv/bin/ruff check lambdas/ --fix

sort-requirements:
	sort -o lambdas/requirements.txt lambdas/requirements.txt
	sort -o lambdas/requirements-test.txt lambdas/requirements-test.txt

check-packages:
	./lambdas/venv/bin/pip-audit -r lambdas/requirements.txt
	./lambdas/venv/bin/pip-audit -r lambdas/requirements-test.txt

test-unit:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/

test-unit-coverage:
	cd ./lambdas && ./venv/bin/python3 -m pytest --cov=. --cov-report xml:coverage.xml

test-unit-coverage-html:
	cd ./lambdas
	coverage run --source=. --omit=tests/* -m pytest -v tests && coverage report && coverage html

test-unit-collect:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/ --collect-only

env:
	rm -rf lambdas/venv || true
	python3 -m venv ./lambdas/venv
	./lambdas/venv/bin/pip3 install --upgrade pip
	./lambdas/venv/bin/pip3 install -r lambdas/requirements.txt
	./lambdas/venv/bin/pip3 install -r lambdas/requirements-test.txt

zip:
	rm -rf ./lambdas/package_$(lambda_name) || true
	mkdir ./lambdas/package_$(lambda_name)
	./lambdas/venv/bin/pip3 install --platform manylinux2014_x86_64 --only-binary=:all: --implementation cp  -r lambdas/requirements.txt -t ./lambdas/package_$(lambda_name)
	mkdir ./lambdas/package_$(lambda_name)/handlers
	cp -r lambdas/handlers/$(lambda_name).py lambdas/package_$(lambda_name)/handlers
	cp -r lambdas/utils lambdas/package_$(lambda_name)
	cp -r lambdas/models lambdas/package_$(lambda_name)
	cp -r lambdas/services lambdas/package_$(lambda_name)
	cp -r lambdas/repositories lambdas/package_$(lambda_name)
	cp -r lambdas/enums lambdas/package_$(lambda_name)
	cd ./lambdas/package_$(lambda_name); zip -r ../../package_lambdas_$(lambda_name).zip .
	rm -rf ./lambdas/package_$(lambda_name)
	cd ../..

package: format zip

install:
	npm --prefix ./app install --legacy-peer-deps

clean-install:
	npm --prefix ./app ci --legacy-peer-deps

pre-commit: sort-requirements format
	npm exec --prefix ./app lint-staged

start:
	npm --prefix ./app start

storybook:
	npm --prefix ./app run storybook

test-ui:
	npm --prefix ./app run test-all

test-ui-coverage:
	npm --prefix ./app run test-all:coverage

build:
	npm --prefix ./app run build

build-env-check:
	npm --prefix ./app run build-env-check

docker-up:
	docker-compose -f ./app/docker-compose.yml up -d

docker-up-rebuild:
	docker-compose -f ./app/docker-compose.yml up -d --build --force-recreate

docker-down:
	docker-compose -f ./app/docker-compose.yml down

cypress-open:
	TZ=GMT npm --prefix ./app run cypress

cypress-run:
	TZ=GMT npm --prefix ./app run cypress-run

cypress-report:
	TZ=GMT npm --prefix ./app run cypress-report
