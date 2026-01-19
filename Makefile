.PHONY: setup

setup:
	@mkdir -p .spatia/{atoms,geometry,portals,bin,logs}
	@sqlite3 .spatia/sentinel.db "CREATE TABLE IF NOT EXISTS atoms (id TEXT PRIMARY KEY, type TEXT, content TEXT, hash TEXT, domain TEXT DEFAULT 'generic', status INTEGER DEFAULT 0, parent_project TEXT, last_witnessed TEXT);"
	@sqlite3 .spatia/sentinel.db "CREATE TABLE IF NOT EXISTS geometry (atom_id TEXT PRIMARY KEY, x INTEGER, y INTEGER, FOREIGN KEY(atom_id) REFERENCES atoms(id));"
	@echo "Sentinel DB Initialized"
