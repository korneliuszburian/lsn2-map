.PHONY: run test lint typecheck clean

run:
	python -m src.run_pipeline --input data/sample/north_america_generator_mapping_template.xlsx --output data/output

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	pyright src/ tests/

clean:
	rm -rf data/output/

all: lint test run
