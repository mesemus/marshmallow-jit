# GitHub Workflows Quick Reference

## Available Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **Tests** | `test.yml` | Push, PR, Manual | Quick validation with Marshmallow 3 & 4 |
| **CI - Full Matrix** | `ci.yml` | Push, PR, Weekly, Manual | Full matrix: Ubuntu/macOS/Windows |
| **Performance Benchmarks** | `benchmarks.yml` | Push (main), PR, Weekly, Manual | Speed tests & profiling |
| **Release** | `release.yml` | Tags (`v*`), Manual | Build & publish to PyPI |
| **Documentation** | `docs.yml` | Push (main), PR, Manual | Validate docs & code examples |

## Test Matrix

### Quick Tests (`test.yml`)
```
Python: 3.14
Marshmallow: 3, 4
OS: Ubuntu
```

### Full CI (`ci.yml`)
```
Python: 3.14
Marshmallow: 3, 4
OS: Ubuntu, macOS, Windows
```

## Running Locally

### Switch between Marshmallow versions
```bash
# Marshmallow 3
uv sync --group dev --group marshmallow3

# Marshmallow 4
uv sync --group dev --group marshmallow4
```

### Run all checks (matching CI)
```bash
# Linting
uv run ruff check marshmallow_jit tests

# Formatting
uv run ruff format --check marshmallow_jit tests

# Type checking
uv run ty check marshmallow_jit tests

# Tests with coverage
uv run pytest --cov=marshmallow_jit --cov-report=term-missing

# Coverage threshold check
uv run coverage report --fail-under=90
```

### Run benchmarks
```bash
uv run python performance/serialization_speed.py
uv run python profiling/profile_hotspots.py benchmark
```

## Release Process

1. **Update version** in `pyproject.toml`
2. **Commit changes**: `git commit -am "Bump version to X.Y.Z"`
3. **Create tag**: `git tag vX.Y.Z`
4. **Push tag**: `git push origin vX.Y.Z`
5. **Workflow runs automatically**:
   - Runs full CI suite
   - Builds distributions
   - Publishes to PyPI (if configured)
   - Creates GitHub release

## Viewing Results

### GitHub Actions
- Go to **Actions** tab in repository
- Click on workflow run to see details
- Download artifacts (benchmarks, coverage, etc.)

### Coverage Reports
- View in Codecov dashboard
- Or locally: `uv run coverage html` → open `htmlcov/index.html`

### Benchmark Results
- Download from workflow artifacts
- Retained for 30 days
- Compare with previous runs

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Coverage below 90%** | Add tests or review uncovered code |
| **Benchmark failure** | Check for performance regressions |
| **Type check errors** | Update type hints, check ty version |
| **Release fails** | Verify PyPI trusted publishing config |
| **Import errors** | Check dependency group in workflow matches local |

## Workflow Status Badges

Add to README.md:
```markdown
[![Tests](https://github.com/mesemus/torched-marshmallow/actions/workflows/test.yml/badge.svg)](https://github.com/mesemus/torched-marshmallow/actions/workflows/test.yml)
[![CI](https://github.com/mesemus/torched-marshmallow/actions/workflows/ci.yml/badge.svg)](https://github.com/mesemus/torched-marshmallow/actions/workflows/ci.yml)
```

## Manual Workflow Triggers

All workflows support manual dispatch via GitHub UI:
1. Go to **Actions** tab
2. Select workflow from left sidebar
3. Click **Run workflow** button
4. Select branch/options
5. Click **Run workflow**

## Schedule

| Workflow | Day | Time (UTC) | Purpose |
|----------|-----|------------|---------|
| CI - Full Matrix | Monday | 00:00 | Weekly comprehensive check |
| Performance Benchmarks | Sunday | 00:00 | Track performance over time |

---

For detailed information, see [docs/github_workflows.md](./github_workflows.md)
