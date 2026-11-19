# Local Quality Gate — Reporting

The local workflow collects scanner output, normalizes findings, generates an HTML report, and packages reporting artifacts in a timestamped ZIP. Its reporting components are under `quality/Local_Scans/reporting/`, with shared normalization and status utilities under `quality/shared/` and `quality/CI/`.

Run the supported local entrypoint from the consuming repository root on macOS/Linux:

```sh
sh quality/Local_Scans/run-local-checks.sh
```

No `quality/project.json` is required for supported automatic Maven discovery. Reports and scanner work files are generated artifacts and should not be committed.

## Reading results

| Outcome | Interpretation |
| --- | --- |
| `CLEAN` | Scanner ran and reported no findings |
| `FINDINGS` | Scanner ran and reported findings |
| `DISABLED` | Scanner did not run because it was inapplicable or disabled |
| `ERROR` | Scanner failed to execute or its output could not be processed |

**Do not equate `DISABLED` or `ERROR` with a successful scan.** The local workflow is advisory; CI enforcement uses separate policy evaluation. A completed report does not prove that all scanners executed successfully.

The standalone repository's cross-platform GitHub workflow tests reporting-related Python components on Ubuntu, macOS, and Windows. It does **not** verify complete scanner/report execution on native Windows. See [root README](../../../README.md), [local scanning](../README.md), and [CI gate](../../CI/README.md).
