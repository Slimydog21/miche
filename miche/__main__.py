"""Run Miche Platform dev server."""

from __future__ import annotations

import uvicorn

from .web import create_app


def main() -> None:
    uvicorn.run(create_app(), host="0.0.0.0", port=8787)


if __name__ == "__main__":
    main()