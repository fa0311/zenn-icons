# zenn-icons

CDN: <https://cdn.jsdelivr.net/gh/fa0311/zenn-icons@main/dist/>

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run main.py
```

Lint and type check:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
