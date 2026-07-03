# GitHub Actions Workflows

This document describes the CI/CD workflows configured for the marshmallow-jit project.

## Workflows Overview

### 1. **test.yml** - Quick Test Matrix
**Trigger**: Push to main/master/develop, PRs, manual dispatch

Matrix tests the core functionality across:
- **Python versions**: 3.14
- **Marshmallow versions**: 3.x and 4.x

**Jobs**:
- Install dependencies with uv
- Lint with ruff
- Format check with ruff
- Type check with ty
- Run pytest with coverage
- Upload coverage to Codecov (for Python 3.14 + Marshmallow 3 only)
- Enforce 90% coverage threshold

**Use this workflow** for quick validation of PRs.

---

### 2. **ci.yml** - Full CI Matrix
**Trigger**: Push to main/master/develop, PRs, weekly schedule (Monday 00:00 UTC), manual dispatch

Full test matrix across:
- **Python versions**: 3.14
- **Marshmallow versions**: 3.x and 4.x
- **Operating systems**: Ubuntu, macOS, Windows

**Jobs**:
1. **Lint**: Code quality checks with ruff
2. **Type Check**: Static type checking with ty
3. **Test**: Run full test suite on all OS/version combinations
4. **Coverage Report**: Generate coverage report and enforce 90% threshold
5. **Test Summary**: Aggregate results from all jobs

**Use this workflow** for comprehensive validation before releases or major changes.

---

### 3. **benchmarks.yml** - Performance Benchmarks
**Trigger**: Push to main/master, PRs, weekly schedule (Sunday 00:00 UTC), manual dispatch

**Jobs**:
1. **Benchmark**: Run serialization speed tests for both Marshmallow 3 and 4
   - Checks that JIT speedup is at least 2.0x vs plain marshmallow
   - Uploads benchmark results as artifacts (retained for 30 days)

2. **Profiling**: Run detailed profiling analysis
   - Identifies hotspots and performance bottlenecks
   - Uploads profiling results as artifacts

**Use this workflow** to detect performance regressions.

---

### 4. **release.yml** - Release and Publish
**Trigger**: Push tags matching `v*`, manual dispatch

**Jobs**:
1. **Pre-release Tests**: Runs full CI workflow
2. **Build**: Creates source distribution and wheel
3. **Publish to PyPI**: Publishes using trusted publishing (requires PyPI configuration)
4. **GitHub Release**: Creates GitHub release with signed artifacts

**Requirements for PyPI publishing**:
- Configure trusted publishing in PyPI project settings
- Set up `pypi` environment in GitHub repository settings

**Use this workflow** for automated releases when pushing version tags.

---

### 5. **docs.yml** - Documentation Validation
**Trigger**: Push to main/master, PRs, manual dispatch

**Jobs**:
1. **Generate Code Examples**: 
   - Runs `docs/generated_code/dump_jit.py`
   - Verifies generated code is up-to-date
   - Uploads examples as artifacts

2. **Check Docs**:
   - Validates presence of required documentation files
   - Can be extended to check for broken links

**Use this workflow** to ensure documentation stays current.

---

## Workflow Configuration

### Dependency Management
All workflows use [uv](https://github.com/astral-sh/uv) for fast, reliable dependency installation:

```bash
# For Marshmallow 3.x
uv sync --group dev --group marshmallow3

# For Marshmallow 4.x
uv sync --group dev --group marshmallow4
```

### Matrix Strategy
The project uses `strategy.fail-fast: false` to ensure all matrix combinations run even if one fails, providing complete test coverage visibility.

### Coverage Requirements
- **Threshold**: 90% minimum coverage
- **Upload**: Only from Ubuntu + Python 3.14 + Marshmallow 3 to avoid duplicate reports
- **Branch coverage**: Enabled via `tool.coverage.run.branch = true`

---

## Local Development

### Run tests matching CI
```bash
# Marshmallow 3.x
uv sync --group dev --group marshmallow3
uv run pytest --cov=marshmallow_jit --cov-report=term-missing

# Marshmallow 4.x
uv sync --group dev --group marshmallow4
uv run pytest --cov=marshmallow_jit --cov-report=term-missing
```

### Run linting and formatting
```bash
uv run ruff check marshmallow_jit tests
uv run ruff format marshmallow_jit tests
```

### Run type checking
```bash
uv run ty check marshmallow_jit tests
```

### Run benchmarks
```bash
uv run python performance/serialization_speed.py
uv run python profiling/profile_hotspots.py benchmark
```

---

## Maintenance

### Updating Workflows
When modifying workflows:
1. Test locally using [act](https://github.com/nektos/act) or push to a feature branch
2. Ensure all required secrets and environments are configured
3. Update this documentation if workflow behavior changes

### Adding New Python Versions
When Python 3.15+ becomes available:
1. Update `python-version` matrix in `test.yml` and `ci.yml`
2. Update `requires-python` in `pyproject.toml`
3. Test compatibility before merging

### Marshmallow Version Support
When Marshmallow 5.x is released:
1. Add `marshmallow5` dependency group in `pyproject.toml`
2. Add to test matrix in workflows
3. Update compatibility layer in `marshmallow_jit/compat.py`

---

## Troubleshooting

### Coverage Upload Fails
- Verify Codecov token is configured in repository secrets
- Check that workflow has `id-token: write` permission

### Type Checking Fails
- Ensure `ty` is updated: `uv add --group dev ty@latest`
- Check Python version compatibility

### Benchmark Failures
- Review profiling output: download artifacts from failed workflow run
- Check if recent changes introduced performance regressions
- Adjust threshold if expected (document reasoning in PR)

### Release Workflow Fails
- Verify tag format: must start with `v` (e.g., `v0.1.0`)
- Check PyPI trusted publishing configuration
- Ensure all tests pass before tagging

---

## Best Practices

1. **Always run tests locally** before pushing
2. **Use conventional commits** for clear change tracking
3. **Add tests for new features** to maintain coverage
4. **Update benchmarks** if optimizations are made
5. **Keep dependencies updated** using `uv lock --upgrade`
6. **Document breaking changes** in release notes
