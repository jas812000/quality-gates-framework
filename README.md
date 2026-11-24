# Quality Gates Framework

Reusable local static-analysis and security-scanning components, result normalization, HTML reporting, and CI policy evaluation. The framework is a standalone, reusable project. Native orchestration is implemented for macOS, Linux and Windows; real scanner acceptance is verified on macOS and pending on Linux and Windows.

## Current capabilities

- Copy the complete `quality/` directory into a host repository. Keep its internal structure intact.
- On macOS and Linux, launch the **advisory** local scan from the host repository root:

  ```sh
  sh quality/Local_Scans/run-local-checks.sh
  ```

- On Windows, run `quality\Local_Scans\run-local-checks.bat` from the host root. On all platforms, use `python -m quality.Local_Scans.run_local_checks` with the scanner environment active. No Git Bash or WSL shell is required by the native launcher.
- Ten scanners: Checkstyle, PMD, SpotBugs, Pylint, Bandit, Gitleaks, TruffleHog, HTMLHint, Stylelint and Trivy. Trivy scans vulnerabilities, misconfigurations and secrets.
- `quality/project.json` is **optional**. The launcher discovers Maven modules containing Java sources under `src/main/java`; it supports multiple source-bearing Maven modules. It does not automatically support Gradle or arbitrary Java layouts.
- Local scanner results distinguish `PASSED`, `FAILED`, `SKIPPED`, `DISABLED`, and `ERROR`. An inapplicable or failed scanner must not be reported as a clean scan.
- The CI normalization, policy, and reporting code is present, but the standalone repository's regression-test workflow is **not** a complete host-repository scanning workflow.

## Prerequisites and limitations

Python 3.11 is recommended for the pinned scanner dependencies. A POSIX shell is needed only for the optional POSIX launcher. Scanner-specific tools may include Java/JDK, Maven or Maven Wrapper, Node.js/npm, Python packages, Docker, and network access for downloads. Missing prerequisites can produce scanner errors; copying the directory alone does not install all third-party tools. See [portability and dependencies](quality/PORTABILITY.md).

TruffleHog prefers a native executable and can fall back to Docker with Linux-container support. Arbitrary host-project layouts have not been certified. Reports default to `~/Downloads/quality-gates-reports/`; archives contain normalized scanner results, consolidated reports and available diagnostics, not raw secret scanner output. Local findings are advisory; execution errors return exit code 2.

## Optional configuration

For ordinary supported Maven layouts, **do not create a configuration file just to get started**. For deliberate overrides, copy `quality/project.example.json` to `quality/project.json` and edit it. The example contains no project-specific path assumptions. Keep credentials out of configuration. Configuration and security-exception details are in [PORTABILITY.md](quality/PORTABILITY.md).

## Tests and cross-platform verification

The repository's [Framework regression tests](.github/workflows/framework-tests.yml) workflow runs shared, CI and native local Python tests on **Ubuntu, macOS, and Windows**, and runs local launcher tests plus shell syntax checks on **Ubuntu and macOS**. It also exercises Java project discovery without `quality/project.json`.

This is a **regression test matrix, not end-to-end scanner certification**. The separate [real scanner acceptance workflow](.github/workflows/scanner-acceptance.yml) runs positive and clean fixtures, platform checks and generated HTML/CSS validation. Linux and Windows jobs run independently; remote results are pending. The macOS local acceptance and generated report checks have passed.

Run the Python tests from this repository's root:

```sh
python -m unittest discover -s quality/shared/tests -p 'test_*.py' -q
python -m unittest discover -s quality/CI/tests -p 'test_*.py' -q
python -m unittest discover -s quality/Local_Scans/tests -p 'test_*.py' -q
```

POSIX-specific checks are restricted to applicable environments. Run real acceptance with `python -m quality.Local_Scans.platform_acceptance` and generated report validation with `python -m quality.shared.reporting.validate_generated` after installing the documented prerequisites.

## Documentation

- [Integration and portability](quality/PORTABILITY.md)
- [Local scanner runner](quality/Local_Scans/README.md)
- [Scanner wrappers](quality/Local_Scans/checks/checks_README.md)
- [Optional Git hooks](quality/Local_Scans/hooks/hooks_README.md)
- [Local reporting](quality/Local_Scans/reporting/report_README.md)
- [CI normalization and policy](quality/CI/README.md)

## License

MIT License. Copyright (c) 2026 James Stevens. See [LICENSE](LICENSE). The distributable `quality/` directory also contains its own license copy.
