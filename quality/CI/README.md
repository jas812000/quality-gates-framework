# CI Quality Gate — Normalization, Policy, and Reporting

The framework includes CI scanner parsers, scanner execution-status contracts, normalization, a policy engine (`quality/CI/gate/policy.yaml`), and report generation. Policy-driven CI enforcement is distinct from the advisory local launcher.

## What is included

- Scanner artifact parsing and normalization in `quality/CI/gate/`.
- Policy evaluation and reporting components.
- Unit tests in `quality/CI/tests/`.
- A **framework regression-test** workflow in the standalone repository: `.github/workflows/framework-tests.yml`.

The standalone workflow runs Python regression tests on Ubuntu, macOS, and Windows. It is **not** a reusable host-project scanner workflow and does not execute all scanners or establish native Windows scanning. An earlier EPMS-specific `build-and-analyze.yml` workflow is **not bundled** with the standalone `quality/` directory. Do not assume copying `quality/` automatically installs GitHub Actions scanning or branch protection.

## Integrating CI in a host project

Copy the complete `quality/` directory. Design a host-specific GitHub Actions workflow that runs the applicable scanner commands, writes the expected raw artifacts and scanner-status records, invokes normalization/policy/reporting, and uploads reports. Verify its behavior on a clean checkout before requiring it for pull requests. A complete portable host-workflow template has not yet been implemented or validated.

The scanner status contract must distinguish execution errors from findings and intentional non-applicability. Missing or malformed scanner artifacts must not be treated as successful clean scans. Policy and scanner enforcement settings must be reviewed before use in a production repository.

`quality/project.json` is optional for the local supported Maven discovery path; creating it is not a prerequisite for running the framework's Python regression tests. Optional source overrides and narrowly justified JDBC exceptions are documented in [PORTABILITY.md](../PORTABILITY.md). Do not put secrets in configuration.

## Regression tests

From the standalone framework repository root:

```sh
python -m unittest discover -s quality/CI/tests -p 'test_*.py' -q
```

See [root README](../../README.md), [portability](../PORTABILITY.md), and [local scanning](../Local_Scans/README.md).

## License

MIT License, copyright (c) 2026 James Stevens. See `quality/LICENSE`. Third-party tools retain their own licenses.
