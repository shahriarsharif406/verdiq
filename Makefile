# Thin wrapper over verdiq.py so the same tasks work on Windows, macOS and Linux.
PY ?= python

.PHONY: setup data test replay chain run shots all clean
setup: ; $(PY) verdiq.py setup
data: ; $(PY) verdiq.py data
test: ; $(PY) verdiq.py test
replay: ; $(PY) verdiq.py replay
chain: ; $(PY) verdiq.py chain
run: ; $(PY) verdiq.py run
shots: ; $(PY) verdiq.py shots
all: ; $(PY) verdiq.py all
clean: ; rm -rf data/out artifacts cache .pytest_cache
