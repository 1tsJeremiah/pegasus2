"""Entry point for running the Codex CLI with `python -m codex_vector`."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
