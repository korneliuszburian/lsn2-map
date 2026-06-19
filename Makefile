SAMPLE_INPUT ?= data/sample/north_america_generator_mapping_template.xlsx
CLIENT_INPUT ?= data/input/clients.xlsx
OUTPUT_DIR ?= data/output
MAP_IMAGE ?= data/assets/client-map/north-america-map-ai-web.png
PORT ?= 8017

.PHONY: reference reference-force run run-demo run-auto run-parquet-sample run-prod map-options map-geographic prototype prototype-geographic serve preview test lint typecheck clean all

reference:
	python -m src.build_reference --output data/reference/postal_reference.parquet

reference-force:
	python -m src.build_reference --output data/reference/postal_reference.parquet --force

run: run-demo

run-demo:
	python -m src.run_pipeline --input $(SAMPLE_INPUT) --output $(OUTPUT_DIR) --reference-mode mock

run-auto:
	python -m src.run_pipeline --input $(SAMPLE_INPUT) --output $(OUTPUT_DIR) --reference-mode auto

run-parquet-sample:
	python -m src.run_pipeline --input $(SAMPLE_INPUT) --output $(OUTPUT_DIR) --reference-mode parquet

run-prod:
	python -m src.run_pipeline --input $(CLIENT_INPUT) --output $(OUTPUT_DIR) --reference-mode parquet

map-options:
	python -m src.render_lsn_map_options --input $(OUTPUT_DIR)/clients_geocoded.csv --map-image $(MAP_IMAGE) --output $(OUTPUT_DIR)/lsn-map-options.html

map-geographic:
	python -m src.render_lsn_geographic_map --input $(OUTPUT_DIR)/clients_geocoded.csv --output $(OUTPUT_DIR)/lsn-map-geographic.html --basemap-output $(OUTPUT_DIR)/lsn-north-america-geographic.svg

prototype: run-demo map-options

prototype-geographic: run-demo map-geographic

serve:
	python -m http.server $(PORT) --bind 127.0.0.1 --directory $(OUTPUT_DIR)

preview: prototype serve

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	pyright src/ tests/

clean:
	rm -rf data/output/

all: lint test prototype
