#!/usr/bin/env python3
"""Quick demo to test the new autocomplete format."""

import asyncio
from openhands_cli.refactor.textual_app import OpenHandsApp

async def main():
    app = OpenHandsApp()
    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())