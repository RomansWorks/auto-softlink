.PHONY: build-docker
build-docker:
	docker build -t tnc_analyzer .

.PHONY: run-docker
run-docker:
	docker run -p 1007:1007 --rm --env-file .env tnc_analyzer

.PHONY: run-docker-detached
run-docker-detached:
	docker run -d -p 1007:1007 --rm --env-file .env tnc_analyzer

.PHONY: run-docker-interactive
run-docker-interactive:
	docker run -it -p 1007:1007 --rm --env-file .env tnc_analyzer

.PHONY: build-docker-dev
build-docker-dev:
	docker build -t tnc_analyzer:dev -f Dockerfile.dev .

.PHONY: run-docker-dev
run-docker-dev:
	docker run -p 1007:1007 --rm --env-file .env -v .:/app tnc_analyzer:dev

.PHONY: run-local
run-local:
	uvicorn src.serving.serving:app --host 0.0.0.0 --port 1007 --reload
