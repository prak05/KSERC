PY      ?= .venv/bin/python
PIP     ?= .venv/bin/pip
REGION  ?= ap-south-1
TF      := terraform -chdir=infra/aws

.PHONY: setup run dev test build docker up deploy-aws plan-aws destroy-aws

## Local ────────────────────────────────────────────────────────────────
setup:                 ## Python venv + UI dependencies
	python3 -m venv .venv && $(PIP) install -r requirements.txt
	cd frontend && npm ci
	[ -f .env ] || cp .env.example .env

build:                 ## Build the UI into frontend/dist (served by FastAPI)
	cd frontend && npm run build

run: build             ## One process on http://localhost:8000
	$(PY) -m uvicorn app:app --host 127.0.0.1 --port 8000

dev:                   ## API on :8000 with reload + Vite on :3000
	$(PY) -m uvicorn app:app --reload --port 8000 & cd frontend && npm run dev

test:
	LLM_PROVIDER=offline $(PY) -m pytest -q tests

docker:                ## Production image
	docker build -t kserc-truing-up .

up:                    ## App + local model server (Ollama) on http://localhost:8080
	docker compose up --build

## AWS ──────────────────────────────────────────────────────────────────
plan-aws:
	$(TF) init -upgrade && $(TF) plan -var region=$(REGION) -out tfplan

deploy-aws:            ## Provision (Terraform) → push image (ECR) → roll out (ECS)
	./scripts/deploy-aws.sh $(REGION)

destroy-aws:
	$(TF) destroy -var region=$(REGION)
