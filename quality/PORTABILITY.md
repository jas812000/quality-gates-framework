# Quality Gates — Integration and Portability

## Installation model

Copy the **entire** `quality/` directory into the root of the consuming repository. Do not copy only `Local_Scans/`; it depends on `CI/` and `shared/`. Do not overwrite an existing `quality/` directory without reviewing it. Do not copy generated reports, tool downloads, `__pycache__`, or secrets.

The project is intended to become plug-and-play. **Today, installation and complete scanner execution are not yet verified across arbitrary host repositories.** The scanner dependencies still require suitable local tools or downloads.

## Run locally

From the host repository root:

```sh
sh quality/Local_Scans/run-local-checks.sh
```

On Windows use `quality\Local_Scans\run-local-checks.bat`. On any platform use `python -m quality.Local_Scans.run_local_checks`. The local workflow is advisory: findings alone return 0; scanner execution or report errors return 2.

## Automatic discovery

`quality/project.json` is **not required**. With no explicit Java path overrides, the launcher discovers Maven modules containing Java files in `src/main/java`, including multiple modules. It ignores generated/vendor directories. A Java repository without a supported Maven layout is **not** evidence that Java scanning succeeded; unsupported layouts require attention. Non-Java scanners use their own source discovery and prerequisite checks.

Inspect Java discovery from the host root:

```sh
python3 -m quality.project_discovery --json .
```

This discovery command reports layout information; it does not run scanners.

## Optional overrides

Only create a configuration when you need explicit project-specific settings:

```sh
cp quality/project.example.json quality/project.json
```

The example includes a project name, scan root, and empty `safe_jdbc_urls` list. The configuration loader also supports validated source/build overrides. Paths must remain inside the host repository. Do not put secrets in the file. JDBC exception entries are security-sensitive; only use narrowly justified values and review their effect on secret-detection policy. The absence of a configuration file must not imply any JDBC exception.

## Tool requirements

- **Base:** Git, Python 3.11 recommended, optional POSIX launcher on macOS/Linux, writable report directory.
- **Java scanning:** compatible JDK and Maven/Maven Wrapper; Checkstyle, PMD, and SpotBugs use native Python orchestration and may download distributions.
- **Python scanning:** scanner packages listed in `quality/Local_Scans/requirements-scanners.txt`.
- **Frontend scanning:** Node.js/npm and applicable HTML/CSS source for HTMLHint/Stylelint.
- **Secret scanning:** Gitleaks runtime; TruffleHog prefers a native executable, with Docker as fallback.
- **Trivy:** native executable for vulnerability, misconfiguration and secret scanning.
- Network access may be required for first-time scanner downloads.

Missing dependencies are not equivalent to a clean scan. Review the report and scanner status artifacts.

## Operating systems

| Environment | Current status |
| --- | --- |
| macOS | Native orchestration and real local acceptance verified |
| Linux | Native orchestration implemented; real acceptance pending |
| Windows | Native batch/Python launcher implemented; real acceptance pending |

The standalone repository's `.github/workflows/framework-tests.yml` tests shared, CI and local Python components on Ubuntu/macOS/Windows and POSIX launcher components on Ubuntu/macOS. **It is not a host-project CI scanning workflow.** Integrating the policy-driven CI gate into another repository requires a separately reviewed workflow and scanner-artifact setup.

## Further documentation

See [local scanning](Local_Scans/README.md), [scanner wrappers](Local_Scans/checks/checks_README.md), [hooks](Local_Scans/hooks/hooks_README.md), [reporting](Local_Scans/reporting/report_README.md), and [CI policy](CI/README.md).
