.PHONY: demo clean test

demo:
	coverage run -m pytest -q example/target_repo
	coverage xml -o example/target_repo/coverage.xml
	python -m qa_copilot analyze example/target_repo --coverage example/target_repo/coverage.xml
	python -m qa_copilot generate example/target_repo --top-k 3
	python -m qa_copilot validate example/target_repo --mut --time-budget 5 --keep-threshold 2.0
	python -m qa_copilot report example/target_repo --out report
	@echo "Open report/index.html"

clean:
	rm -rf report .coverage .pytest_cache **/__pycache__ \
	       example/target_repo/.coverage example/target_repo/coverage.xml \
	       example/target_repo/tests/autogen \
	       example/target_repo/.qa_copilot_targets.json \
	       example/target_repo/.qa_copilot_created.json \
	       example/target_repo/.qa_copilot_validate.json \
	       example/target_repo/.qa_copilot_ledger.json

test:
	pytest -q
