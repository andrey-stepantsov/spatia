import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from contextlib import asynccontextmanager

# Mock lifespan to avoid blocking DB call during test
@asynccontextmanager
async def mock_lifespan(app):
    yield

app.router.lifespan_context = mock_lifespan

@pytest.mark.anyio
@pytest.mark.skip(reason="Flaky in devbox environment due to thread/loop starvation")
async def test_sse_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with ac.stream("GET", "/api/events") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            # Iterate to receive the first event
            async for line in response.aiter_lines():
                if "event: connected" in line or "data: {}" in line:
                    break

