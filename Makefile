PY ?= .venv/bin/python

.PHONY: all quick data validate analysis report notebooks dashboard screenshots sql clean

all:            ## full pipeline: SQL -> tables -> analysis -> report, memo, notebooks
	$(PY) run.py

quick:          ## everything except executing the notebooks
	$(PY) run.py --skip-notebooks

sql:            ## build the DuckDB warehouse only (sql/01-09)
	$(PY) -m src.sql_runner

validate:       ## download CMS FY2026/FY2027 penalty files and compare (optional)
	$(PY) -m src.validate_cms --download

dashboard:      ## launch the Streamlit demo app
	$(PY) -m streamlit run dashboard/app.py

screenshots:    ## regenerate README screenshots (needs requirements-dev.txt + playwright install chromium)
	$(PY) scripts/screenshots.py

clean:          ## remove cached data (raw CMS files are never touched)
	rm -rf data/processed data/warehouse.duckdb
