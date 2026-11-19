"""Native packet-loss recovery regression: python -m tests.smoke_retransmission.

Drops one synthetic-video packet after the sender's RTX cache, requires that
exact sequence to return as RTX, then waits for ten more decoded frames.
"""

import asyncio

from tests.smoke_media import run

if __name__ == "__main__":
    asyncio.run(run(verify_retransmission=True))
