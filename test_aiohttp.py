import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

async def main():
    class MockResp:
        def __init__(self, status, json_data):
            self.status = status
            self.json_data = json_data
        async def json(self): return self.json_data
        async def text(self): return json.dumps(self.json_data)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass

    class MockSession:
        def __init__(self):
            # MagicMock instead of AsyncMock for the context manager provider
            self.get = MagicMock(return_value=MockResp(200, {"score": "25.5", "status": "done"}))

    session = MockSession()

    async with session.get("http://example.com") as resp:
        print(await resp.json())
        print(resp.status)

asyncio.run(main())
