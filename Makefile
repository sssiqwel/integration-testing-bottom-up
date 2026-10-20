VENV   ?= .venv
PYTHON ?= $(VENV)/bin/python

export PYTHON

.PHONY: install test defects clean

$(VENV)/bin/python:
	python3 -m venv $(VENV)

install: $(VENV)/bin/python
	$(PYTHON) -m pip install -r requirements.txt

test:
	sh run_stages.sh

defects:
	$(PYTHON) -m pytest -v -m defect --runxfail --tb=line -p no:cacheprovider || true

clean:
	rm -rf .pytest_cache tests/__pycache__
