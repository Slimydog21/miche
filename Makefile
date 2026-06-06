.PHONY: check test-pytest test-e2e capstone

check:
	bash scripts/check_platform.sh

test-pytest:
	uv run pytest -q

test-e2e:
	npm run test:e2e:island

capstone:
	bash harness/miche_platform_capstone_drill.sh --cassette