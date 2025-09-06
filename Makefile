dev:
	python -m pytest -q || true
	python -m pip -q install -r requirements.txt
	python -m pip -q install pre-commit || true
	pre-commit install || true
