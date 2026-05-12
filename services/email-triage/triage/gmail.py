"""Gmail client factory.

Picks between the IMAP and MCP implementations at runtime based on which
credentials are configured. Both implementations expose the same surface
(``list_recent``, ``get_message``, ``apply_label``, ``create_draft``), so
``poll.py`` can stay implementation-agnostic.

Selection rule: IMAP wins if ``GMAIL_APP_PASSWORD`` (and ``GMAIL_USER``)
are set; otherwise we fall back to the MCP path. ``config.load_config``
already enforces that at least one set is provided.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Union

from .config import Config
from .gmail_imap import GmailImap, connect_gmail_imap
from .gmail_mcp import GmailMcp, connect_gmail_mcp


@asynccontextmanager
async def connect_gmail(
    cfg: Config,
) -> AsyncIterator[Union[GmailMcp, GmailImap]]:
    if cfg.gmail_app_password and cfg.gmail_user:
        async with connect_gmail_imap(cfg.gmail_user, cfg.gmail_app_password) as g:
            yield g
    else:
        async with connect_gmail_mcp(cfg.gmail_mcp_command or "", cfg.gmail_mcp_args) as g:
            yield g
