"""OpenHands ACP Main Entry Point."""

import asyncio
import logging
import os
from datetime import datetime

from openhands.sdk.logger import DEBUG

from .agent import run_acp_server


def setup_logging_and_redirect() -> None:
    """Setup logging based on DEBUG flag.

    Note: stdin/stdout/stderr are NOT redirected as they may be used by:
    - stdio_streams() for ACP protocol communication
    - Parent processes for capturing output during testing
    Only Python's logging output is configured to go to file or devnull.
    """
    if DEBUG:
        # When DEBUG is true, configure logging to log file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        log_file = f"openhands_acp_{timestamp}.log"
        log_fd = open(log_file, "a")

        # Configure logging to log file only (don't touch sys.stderr)
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(log_fd)],
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Debug mode enabled, logging to {log_file}")
    else:
        # When DEBUG is false, configure logging to /dev/null (don't touch sys.stderr)
        devnull = open(os.devnull, "w")

        # Configure logging to /dev/null only
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(devnull)],
        )


async def run_acp_agent() -> None:
    """Run the ACP agent server (alias for run_acp_server)."""
    setup_logging_and_redirect()
    await run_acp_server()


if __name__ == "__main__":
    setup_logging_and_redirect()
    asyncio.run(run_acp_server())
