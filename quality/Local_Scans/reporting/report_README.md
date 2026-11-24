# Local Quality Gate — Reporting

The local workflow collects scanner output, normalizes findings, generates an HTML report, and packages reporting artifacts in a timestamped ZIP. Its reporting components are under `quality/Local_Scans/reporting/`, with shared normalization and status utilities under `quality/shared/` and `quality/CI/`.

Run the supported local entrypoint from the consuming repository root on macOS/Linux:

```sh
sh quality/Local_Scans/run-local-checks.sh
```

On Windows use `quality\Local_Scans\run-local-checks.bat`, or use `python -m quality.Local_Scans.run_local_checks` on any platform.

No `quality/project.json` is required for supported automatic Maven discovery. Reports and scanner work files are generated artifacts and should not be committed.

## Reading results

| Outcome | Interpretation |
| --- | --- |
| `PASSED` | Scanner ran and reported no findings |
| `FAILED` | Scanner ran and reported findings |
| `DISABLED` | Scanner intentionally disabled |
| `SKIPPED` | No applicable scan targets |
| `ERROR` | Scanner failed to execute or its output could not be processed |

**Do not equate `SKIPPED`, `DISABLED` or `ERROR` with a successful scan.** The local workflow is advisory; CI enforcement uses separate policy evaluation. A completed report does not prove that all scanners executed successfully.

Archives include ten normalized scanner JSON reports, consolidated HTML/JSON, scanner status and available Java diagnostics. Raw secret scanner artifacts are excluded. Generated report HTML and CSS are validated separately with `python -m quality.shared.reporting.validate_generated`.

The standalone repository's cross-platform GitHub workflow tests reporting-related Python components on Ubuntu, macOS, and Windows. It does **not** verify complete scanner/report execution on native Windows. See [root README](../../../README.md), [local scanning](../README.md), and [CI gate](../../CI/README.md).
