#!/bin/sh
rm dist/*
uv run python3 -m build
uv run twine upload dist/*

