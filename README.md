# Quality Gates Framework

Reusable local static-analysis and security-scanning components, result normalization, HTML reporting, and CI policy evaluation. The framework is being extracted from an existing application into a standalone, reusable project; **full plug-and-play portability has not yet been demonstrated**.

## Current capabilities

- Copy the complete `quality/` directory into a host repository. Keep its internal structure intact.
- On macOS and Linux, launch the **advisory** local scan from the host repository root:

  ```sh
  sh quality/Local_Scans/run-local-checks.sh
  ```

- `quality/project.json` is **optional**. The launcher discovers Maven modules containing Java sources under `src/main/java`; it supports multiple source-bearing Maven modules. It does not automatically support Gradle or arbitrary Java layouts.
- Local scanner results distinguish `CLEAN`, `FINDINGS`, `DISABLED`, and `ERROR`. An inapplicable or failed scanner must not be reported as a clean scan.
- The CI normalization, policy, and reporting code is present, but the standalone repository's regression-test workflow is **not** a complete host-repository scanning workflow.

## Prerequisites and limitations

Python 3.10+ and a compatible POSIX shell are needed for the current local launcher. Scanner-specific tools may include Java/JDK, Maven or Maven Wrapper, Node.js/npm, Python packages, Docker, and network access for downloads. Missing prerequisites can produce scanner errors; copying the directory alone does not install all third-party tools. See [portability and dependencies](quality/PORTABILITY.md).

Windows currently has `quality\Local_Scans\run-local-checks.bat`, which delegates to **Git Bash**. Native Windows scanning without a Unix shell is **not implemented or verified**. Python-only, JavaScript-only, and non-Maven projects have not passed complete standalone acceptance testing.

## Optional configuration

For ordinary supported Maven layouts, **do not create a configuration file just to get started**. For deliberate overrides, copy `quality/project.example.json` to `quality/project.json` and edit it. The example contains no project-specific path assumptions. Keep credentials out of configuration. Configuration and security-exception details are in [PORTABILITY.md](quality/PORTABILITY.md).

## Tests and cross-platform verification

The repository's [Framework regression tests](.github/workflows/framework-tests.yml) workflow runs shared and CI Python tests on **Ubuntu, macOS, and Windows**, and runs local launcher tests plus shell syntax checks on **Ubuntu and macOS**. It also exercises Java project discovery without `quality/project.json`.

This is a **regression test matrix, not end-to-end scanner certification**. It does not establish native Windows scanner support or prove that every scanner runs in a newly cloned host project. The workflow must run on GitHub before its operating-system results can be reported as verified.

Run the Python tests from this repository's root:

```sh
python -m unittest discover -s quality/shared/tests -p 'test_*.py' -q
python -m unittest discover -s quality/CI/tests -p 'test_*.py' -q
python -m unittest discover -s quality/Local_Scans/tests -p 'test_*.py' -q
```

Some local launcher tests require a POSIX environment. The framework's GitHub workflow intentionally does not run them on Windows.

## Documentation

- [Integration and portability](quality/PORTABILITY.md)
- [Local scanner runner](quality/Local_Scans/README.md)
- [Scanner wrappers](quality/Local_Scans/checks/checks_README.md)
- [Optional Git hooks](quality/Local_Scans/hooks/hooks_README.md)
- [Local reporting](quality/Local_Scans/reporting/report_README.md)
- [CI normalization and policy](quality/CI/README.md)

## License

MIT License. Copyright (c) 2026 James Stevens. See [LICENSE](LICENSE). The distributable `quality/` directory also contains its own license copy.
