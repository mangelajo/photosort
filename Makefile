distribute:
	rm dist/*
	uv run python3 -m build
	uv run twine upload dist/*

test:
	for python in 3.9 3.10 3.11 3.12; do \
		echo "Testing on python $$python"; \
		uv run -p $$python pytest; \
	done

sync:
	uv sync

install-uv:
	curl -LsSf https://astral.sh/uv/install.sh | sh

container-build:
	podman build -t photosort:latest -f Containerfile .

container-run:
	podman run --rm -it photosort:latest