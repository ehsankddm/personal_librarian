# UV Usage Guide

This project uses [uv](https://github.com/astral-sh/uv) for fast and reliable Python project management.

## Quick Start

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync all dependencies (recommended)
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Unix/Mac
.venv\Scripts\activate     # On Windows

# Run the application
python run_dev.py
```

## Common Commands

### Dependency Management

```bash
# Install all dependencies (prod + dev)
uv sync

# Install only production dependencies
uv sync --no-dev

# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Add a specific version
uv add "package-name>=1.2.0"

# Remove a dependency
uv remove package-name

# Update all dependencies
uv sync --upgrade

# Show dependency tree
uv tree
```

### Virtual Environment

```bash
# Create virtual environment (handled by uv sync)
uv venv

# Activate virtual environment
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows

# Run command in virtual environment without activating
uv run python run_dev.py
uv run pytest

# Run any command
uv run black .
uv run ruff check
```

### Development

```bash
# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run ruff check

# Type check
uv run mypy .

# Fix linting issues
uv run ruff check --fix

# Run all checks
uv run black . && uv run ruff check && uv run mypy .
```

### Lock Files

```bash
# Generate or update uv.lock
uv lock

# Update all dependencies in lock file
uv lock --upgrade

# Check for outdated packages
uv lock --check
```

## Why UV?

- **Fast**: Written in Rust, 10-100x faster than pip
- **Reliable**: Deterministic builds with lock files
- **Simple**: Single tool for venv, pip, and packaging
- **Modern**: Compatible with PEP 517/621 standards
- **Secure**: Built-in dependency resolution and conflict detection

## Integration with Other Tools

UV is compatible with standard Python tools:

```bash
# Use with make, justfile, etc.
uv run python script.py

# Use in CI/CD
uv venv
uv pip install -e .
uv run pytest
```

## Troubleshooting

### Clear cache
```bash
uv cache clean
```

### Reinstall everything
```bash
rm -rf .venv
uv sync
```

### Check version
```bash
uv --version
```

## Learn More

- [uv documentation](https://github.com/astral-sh/uv)
- [uv vs pip benchmark](https://astral.sh/blog/uv)
- [Tutorial](https://docs.astral.sh/uv/)

