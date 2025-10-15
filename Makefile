PYTHON_VERSION=3.11

REQUIREMENTS_PATH=lambdas/requirements
LAMBDA_LAYER_REQUIREMENTS_PATH=$(REQUIREMENTS_PATH)/layers

GITHUB_REQUIREMENTS=$(REQUIREMENTS_PATH)/requirements_github_runner.txt
TEST_REQUIREMENTS=$(REQUIREMENTS_PATH)/requirements_test.txt
CORE_REQUIREMENTS=$(LAMBDA_LAYER_REQUIREMENTS_PATH)/requirements_core_lambda_layer.txt
DATA_REQUIREMENTS=$(LAMBDA_LAYER_REQUIREMENTS_PATH)/requirements_data_lambda_layer.txt
REPORTS_REQUIREMENTS=$(LAMBDA_LAYER_REQUIREMENTS_PATH)/requirements_reports_lambda_layer.txt
ALERTING_REQUIREMENTS=$(LAMBDA_LAYER_REQUIREMENTS_PATH)/requirements_alerting_lambda_layer.txt
EDGE_REQUIREMENTS=$(REQUIREMENTS_PATH)/requirements_edge_lambda.txt
LAMBDAS_BUILD_PATH=build/lambdas
LAMBDA_LAYERS_BUILD_PATH=build/lambda_layers
LAMBDA_LAYER_PYTHON_PATH=python/lib/python$(PYTHON_VERSION)/site-packages

ZIP_BASE_PATH = ./$(LAMBDAS_BUILD_PATH)/$(lambda_name)/tmp
ZIP_COMMON_FILES = lambdas/utils lambdas/models lambdas/services lambdas/repositories lambdas/enums

default: help

help: ## This help message
		@grep -E --no-filename '^[a-zA-Z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-42s\033[0m %s\n", $$1, $$2}'

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
	sort -o $(TEST_REQUIREMENTS) $(TEST_REQUIREMENTS)
	sort -o $(CORE_REQUIREMENTS) $(CORE_REQUIREMENTS)
	sort -o $(DATA_REQUIREMENTS) $(DATA_REQUIREMENTS)
	sort -o $(REPORTS_REQUIREMENTS) $(REPORTS_REQUIREMENTS)
	sort -o $(ALERTING_REQUIREMENTS) $(ALERTING_REQUIREMENTS)


check-packages:
	./lambdas/venv/bin/pip-audit -r $(TEST_REQUIREMENTS)
	./lambdas/venv/bin/pip-audit -r $(CORE_REQUIREMENTS)
	./lambdas/venv/bin/pip-audit -r $(DATA_REQUIREMENTS)
	./lambdas/venv/bin/pip-audit -r $(REPORTS_REQUIREMENTS)
	./lambdas/venv/bin/pip-audit -r $(ALERTING_REQUIREMENTS)

test-api-e2e:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/e2e/api -vv

test-api-e2e-snapshots:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/e2e/api --snapshot-update

test-bulk-upload-e2e:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/e2e/bulk_upload -vv

test-unit: ## Run unit tests.
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/unit

test-unit-coverage:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/unit --cov=. --cov-report xml:coverage.xml

test-unit-coverage-html:
	cd ./lambdas && coverage run --source=. --omit="tests/*" -m pytest -v tests/unit && coverage report && coverage html

test-unit-collect:
	cd ./lambdas && ./venv/bin/python3 -m pytest tests/unit --collect-only

env: ## build a virtual environment.
	rm -rf lambdas/venv || true
	python3 -m venv ./lambdas/venv
	./lambdas/venv/bin/pip3 install --upgrade pip
	./lambdas/venv/bin/pip3 install -r $(TEST_REQUIREMENTS) --no-cache-dir
	./lambdas/venv/bin/pip3 install -r $(CORE_REQUIREMENTS) --no-cache-dir
	./lambdas/venv/bin/pip3 install -r $(DATA_REQUIREMENTS) --no-cache-dir
	./lambdas/venv/bin/pip3 install -r $(REPORTS_REQUIREMENTS) --no-cache-dir
	./lambdas/venv/bin/pip3 install -r $(ALERTING_REQUIREMENTS) --no-cache-dir

destroy-env: ## Destroy a virtual environment.
	deactivate
	rm -rf lambdas/venv || true

github_env:
	rm -rf lambdas/venv || true
	python3 -m venv ./lambdas/venv
	./lambdas/venv/bin/pip3 install --upgrade pip
	./lambdas/venv/bin/pip3 install -r $(GITHUB_REQUIREMENTS) --no-cache-dir

edge_env:
	rm -rf lambdas/venv || true
	python3 -m venv ./lambdas/venv
	./lambdas/venv/bin/pip3 install --upgrade pip
	./lambdas/venv/bin/pip3 install -r $(GITHUB_REQUIREMENTS) --no-cache-dir
	./lambdas/venv/bin/pip3 install -r $(EDGE_REQUIREMENTS) --no-cache-dir

zip:
	echo $(LAMBDAS_BUILD_PATH)/$(lambda_name)
	rm -rf ./$(LAMBDAS_BUILD_PATH)/$(lambda_name) || true
	mkdir -p $(ZIP_BASE_PATH)/handlers
	cp lambdas/handlers/${lambda_path}/$(lambda_name).py $(ZIP_BASE_PATH)/handlers
	cp -r $(ZIP_COMMON_FILES) $(ZIP_BASE_PATH)
	cd $(ZIP_BASE_PATH) ; zip -r ../$(lambda_name).zip .
	rm -rf $(ZIP_BASE_PATH)

edge_zip: zip
	mkdir -p $(ZIP_BASE_PATH)/python
	cp -r lambdas/venv/lib/python*/site-packages/* $(ZIP_BASE_PATH)
	cd $(ZIP_BASE_PATH) ; zip -r ../$(lambda_name).zip .
	rm -rf $(ZIP_BASE_PATH)

lambda_layer_zip:
	rm -rf ./$(LAMBDA_LAYERS_BUILD_PATH)/$(layer_name) || true
	mkdir -p ./$(LAMBDA_LAYERS_BUILD_PATH)/$(layer_name)
	./lambdas/venv/bin/pip3 install --platform manylinux2014_x86_64 --only-binary=:all: --implementation cp  -r $(LAMBDA_LAYER_REQUIREMENTS_PATH)/requirements_$(layer_name).txt -t ./$(LAMBDA_LAYERS_BUILD_PATH)/$(layer_name)/tmp/$(LAMBDA_LAYER_PYTHON_PATH)
	cd ./$(LAMBDA_LAYERS_BUILD_PATH)/$(layer_name)/tmp; zip -r ../$(layer_name).zip .
	rm -rf ./$(LAMBDA_LAYERS_BUILD_PATH)/$(layer_name)/tmp
	cd ../..

package: format zip

install:
	npm --prefix ./app install --legacy-peer-deps
	cp ./app/node_modules/pdfjs-dist/build/pdf.worker.min.mjs ./app/public/

clean-install:
	npm --prefix ./app ci --legacy-peer-deps

install-pdfjs:
	mkdir -p ./app/public/pdfjs
	wget https://github.com/mozilla/pdf.js/releases/download/v4.10.38/pdfjs-4.10.38-dist.zip -O ./app/public/pdfjs/pdfjs.zip
	unzip -o -d ./app/public/pdfjs ./app/public/pdfjs/pdfjs.zip
	rm ./app/public/pdfjs/pdfjs.zip

start:
	npm --prefix ./app start

test-ui:
	npm --prefix ./app run test-all

test-ui-coverage:
	npm --prefix ./app run test-all:coverage

build:
	npm --prefix ./app run build

build-env-check:
	npm --prefix ./app run build-env-check

docker-up: ## Run docker container.
	docker-compose -f ./app/docker-compose.yml up -d

docker-up-rebuild: ## Rebuild docker container.
	docker-compose -f ./app/docker-compose.yml up -d --build --force-recreate

docker-down: ## Destroy docker container. 
	docker-compose -f ./app/docker-compose.yml down

cypress-open:
	TZ=GMT npm --prefix ./app run cypress

cypress-run:
	TZ=GMT npm --prefix ./app run cypress-run

cypress-report:
	TZ=GMT npm --prefix ./app run cypress-report

