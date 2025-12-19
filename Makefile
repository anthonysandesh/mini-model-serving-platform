.PHONY: install lint test fmt demo up down docker-build k8s-apply k8s-destroy load-features generate-model

PYTHON := python

install:
	$(PYTHON) -m pip install -r requirements.txt -c constraints.txt
	$(PYTHON) -m pip install -r requirements-dev.txt -c constraints.txt || true

fmt:
	ruff format src tests

lint:
	ruff check src tests

test:
	pytest -q

generate-model:
	$(PYTHON) scripts/build_example_model.py

load-features:
	$(PYTHON) scripts/load_features.py

up:
	docker-compose -f infra/docker-compose.yaml up -d

down:
	docker-compose -f infra/docker-compose.yaml down

demo: generate-model up load-features
	$(PYTHON) scripts/send_load.py --duration 10

k8s-apply:
	kubectl apply -k k8s/overlays/dev

k8s-destroy:
	kubectl delete -k k8s/overlays/dev
