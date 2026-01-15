.PHONY: setup shell clean-atoms

setup:
	@printf "🚀 Initializing Spatia Infrastructure...\n"
	@mkdir -p .spatia/{atoms,geometry,portals,bin,logs}
	@if [ ! -f .spatia/sentinel.db ]; then \
		sqlite3 .spatia/sentinel.db "CREATE TABLE atoms (id TEXT PRIMARY KEY, type TEXT, content TEXT, hash TEXT);"; \
		sqlite3 .spatia/sentinel.db "CREATE TABLE geometry (atom_id TEXT, pane_id TEXT, x INTEGER, y INTEGER);"; \
		printf "✅ Sentinel DB Initialized.\n"; \
	fi

shell:
	nix develop

clean-atoms:
	rm -rf .spatia/atoms/*
	sqlite3 .spatia/sentinel.db "DELETE FROM atoms;"
