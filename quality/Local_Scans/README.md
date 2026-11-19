# Local Quality Gate

The local quality gate is **advisory**: it runs applicable scanners, collects results, generates HTML and ZIP reporting artifacts, and distinguishes findings from execution errors. It does not apply CI blocking thresholds.

## Start here

Copy the complete `quality/` directory into the host repository. On macOS or Linux, run from the host root:

```sh
sh quality/Local_Scans/run-local-checks.sh
```

No `quality/project.json` is required for the supported default Maven layout. The launcher automatically discovers Maven modules with Java production sources, including multi-module repositories. `quality/project.example.json` is only a starting point for **optional** overrides. Non-Maven Java layouts are not yet automatically supported.

On Windows, `quality\Local_Scans\run-local-checks.bat` requires Git Bash; **native Windows scanning has not been implemented or verified**.

## Scanners

| Scanner | Main use |
| --- | --- |
| Checkstyle | Java style |
| PMD | Java static analysis |
| SpotBugs | Java bytecode defects |
| Pylint | Python quality |
| Bandit | Python security |
| Gitleaks | Secrets |
| TruffleHog | Secrets via Docker |
| HTMLHint | HTML |
| Stylelint | Stylesheets |

Applicability and successful execution are different. Scanner outcomes include `CLEAN`, `FINDINGS`, `DISABLED`, and `ERROR`; an error or disabled scanner is **not** a clean result.

## Dependencies

Python 3.10+, a POSIX shell, and relevant scanner prerequisites are required. Java checks require a JDK and Maven/Maven Wrapper; scanner distributions may be downloaded. Python scanner packages are listed in `requirements-scanners.txt`. Frontend scanners may require Node.js/npm. TruffleHog requires Docker. Missing prerequisites must be diagnosed through scanner status and reports.

## Reporting and hooks

Reports and downloaded tools are generated under `quality/Local_Scans/` and should remain untracked. See [reporting details](reporting/report_README.md). The [pre-commit hook](hooks/hooks_README.md) is **optional** and deliberately does not block commits. The CI policy gate is a separate enforcement mechanism; see [CI documentation](../CI/README.md).

## Tests

From the framework repository root, on macOS/Linux:

```sh
python -m unittest discover -s quality/Local_Scans/tests -p 'test_*.py' -q
```

These are regression tests, not proof of full real-scanner acceptance on all platforms. See the [root README](../../README.md) and [portability guide](../PORTABILITY.md).
