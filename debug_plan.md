
# Issue Analysis
- `curl` failed to connect to port 8000.
- Playwright output shows: `[WebServer] /opt/homebrew/opt/python@3.14/bin/python3.14: No module named uvicorn`.
- This indicates that Playwright's `webServer` config is using the system Python (`python3` -> `/opt/homebrew/.../python3.14`) instead of the `devbox` or `venv` python which has `uvicorn` installed.
- The `reset_env.py` script likely uses the correct python path (hardcoded in my loop?) but Playwright spawns its own server using `python3 -m uvicorn` in `playwright.config.js`.

# Fix Plan
1. Update `playwright.config.js` to use the absolute path to the venv python: `/Users/stepants/dev/spatia/.venv/bin/python3`.
2. Or ensure `devbox run` is used to wrap the playwright command so `python3` resolves correctly.
3. Check `reset_env.py` - if it starts the server but then exits, the server might be dying if not properly daemonized or if `playwright` kills it.

# Immediate Action
- Modify `frontend/playwright.config.js` to use the venv python executable.
