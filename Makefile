distribute:
	rm dist/*
	uv run python3 -m build
	uv run twine upload dist/*

test:
	for python in 3.9 3.10 3.11 3.12 3.13 3.14; do \
		echo "Testing on python $$python"; \
		uv run -p $$python pytest; \
	done

sync:
	uv sync

install-uv:
	curl -LsSf https://astral.sh/uv/install.sh | sh

# Container image configuration
CONTAINER_IMAGE ?= quay.io/mangelajo/photosort
CONTAINER_TAG ?= latest

container-build:
	podman build -t $(CONTAINER_IMAGE):$(CONTAINER_TAG) -f Containerfile .

container-push:
	podman push $(CONTAINER_IMAGE):$(CONTAINER_TAG)

container-run:
	podman run --rm -it $(CONTAINER_IMAGE):$(CONTAINER_TAG)