# Local Quality Gate

The advisory Local Quality Gate supports ten scanners. Native Python orchestration is implemented; real Linux and Windows acceptance is pending. Run from the host repository root. Preserve project-specific rules and `quality/project.json` when installing or upgrading the complete `quality/` directory.

## Installation

Use Python 3.11 for the pinned scanner dependencies. Install Git, a compatible JDK (Java 21 or newer for the current Checkstyle distribution), Maven, Node.js/npm, Gitleaks, Trivy and Docker with Linux-container support. Ensure all executables are on PATH.

### macOS

With Homebrew installed:

```sh
brew install python@3.11 openjdk@21 maven node gitleaks trivy
brew install --cask docker
python3.11 -m venv ~/Downloads/qg-venv
source ~/Downloads/qg-venv/bin/activate
python -m pip install -r quality/Local_Scans/requirements-scanners.txt
```

Start Docker Desktop. Follow Homebrew's JDK PATH instructions.

### Linux (Ubuntu example)

```sh
sudo apt update
sudo apt install git python3 python3-venv openjdk-21-jdk maven nodejs npm
```

Use a distribution or Python installation providing Python 3.11, and a current supported Node.js LTS release. Install Gitleaks from its [release binaries](https://github.com/gitleaks/gitleaks/releases), Trivy using its [official packages](https://trivy.dev/latest/getting-started/installation/), and Docker Engine using [Docker's instructions](https://docs.docker.com/engine/install/). Put the matching architecture binaries on PATH and configure authorized Docker access.

```sh
python3.11 -m venv ~/Downloads/qg-venv
source ~/Downloads/qg-venv/bin/activate
python -m pip install -r quality/Local_Scans/requirements-scanners.txt
```

### Native Windows (PowerShell)

Install Git, Python 3.11, JDK 21+, Maven, Node.js LTS, Docker Desktop, Gitleaks and Trivy using their official installers or release binaries. Configure PATH and JAVA_HOME as required. Docker must run Linux containers; Docker's own virtualization prerequisites are separate from the framework launcher. No Git Bash or WSL shell is required by the launcher.

```powershell
py -3.11 -m venv "$HOME/Downloads/qg-venv"
& "$HOME/Downloads/qg-venv/Scripts/python.exe" -m pip install -r quality/Local_Scans/requirements-scanners.txt
& "$HOME/Downloads/qg-venv/Scripts/python.exe" -m quality.Local_Scans.run_local_checks --no-browser
```

## Scanner installation and verification

| Scanner | Installation | Verification |
| --- | --- | --- |
| Checkstyle | Automatically downloaded JAR | Native Java fixture (Batch E) |
| PMD | Automatically downloaded distribution | Native Java fixture (Batch E) |
| SpotBugs | Automatically downloaded distribution; Maven compilation required | Native Java fixture (Batch E) |
| Pylint | Python requirements | `python -m pylint --version` |
| Bandit | Python requirements | `python -m bandit --version` |
| Gitleaks | Platform release binary | `gitleaks version` |
| TruffleHog | Docker image | `docker run --rm trufflesecurity/trufflehog:3.82.6 --version` |
| HTMLHint | npx downloads package | `npx --yes htmlhint --version` |
| Stylelint | npm provisions local scanner tools | `npx --yes stylelint --version` |
| Trivy | Platform package or release binary | `trivy --version` |

Also verify `java -version`, `mvn --version`, `node --version`, `npm --version`, `docker version`, and `python --version`. Initial downloads require network access. Review scanner versions and rerun acceptance tests before upgrading.

## Run and configure

On macOS/Linux use `python -m quality.Local_Scans.run_local_checks` (or `sh quality/Local_Scans/run-local-checks.sh`). On Windows use the active environment's Python with the same module command, or `quality\Local_Scans\run-local-checks.bat`. Add `--no-browser` for unattended runs.

Optional overrides are documented in `quality/project.example.json`; Maven modules with Java production sources are discovered automatically. Unsupported Java layouts require configuration. Trivy enables vulnerability, misconfiguration and secret scanning, not image or license scanning. Missing coverage evidence is not proof of a clean scan.

## Reports and troubleshooting

Reports default to a repository-name-and-path-hash directory under `~/Downloads/quality-gates-reports/`. `QUALITY_OUTPUT_DIR` may select a dedicated subdirectory under Downloads. Symlink/reparse-point paths are rejected. Each run has a separate session; no previous session is recursively deleted. ZIP exports contain only normalized JSON and HTML. Raw Gitleaks and TruffleHog artifacts are not retained after normalization; temporary scanner data can still exist during execution. Treat local reports and interrupted runs as sensitive. Delete old sessions manually when no scan is running.

Exit 0 means the advisory report was generated, not that every scanner passed. Exit 2 means launcher/report failure. Inspect individual scanner statuses for findings, errors, disabled scanners and coverage diagnostics. CI blocking policy is separate. See [reporting](reporting/report_README.md) and [CI](../CI/README.md).

If Trivy cannot find `docker-credential-desktop`, ensure the configured helper is on PATH. On macOS Docker Desktop may require `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"`. Do not delete credentials. Optional database initialization: `trivy image --download-db-only`. Check network access and registry authentication for download failures.

Run regression tests with `python -m unittest discover -s quality/Local_Scans/tests -p 'test_*.py' -q`. Real cross-platform acceptance is separate.

## Real scanner acceptance

Run `python -m quality.Local_Scans.acceptance --report ~/Downloads/qg-acceptance.json` (PowerShell: use `"$HOME/Downloads/qg-acceptance.json"`). Install all prerequisites first. The fixture requires findings from every scanner and checks Trivy modes and retained report leakage. A missing scanner, missing finding, or report error fails acceptance. This is not a clean-fixture or failure-injection certification.

The manual GitHub Actions acceptance workflow uses a GitHub-hosted Linux runner or dedicated trusted self-hosted Windows/macOS runners labeled `qg-acceptance`, with the documented prerequisites and a running Linux-container Docker engine. Do not register a personal workstation for untrusted repository workflows. Native Windows Python regression tests also run on GitHub-hosted Windows without Bash.

### Release acceptance

The real acceptance command runs both deliberately noncompliant and clean synthetic projects. A successful Trivy scan with a valid report and zero findings passes; category coverage evidence remains diagnostic metadata. Do not interpret a successful process exit as proof of complete coverage. Run the regression workflow on all three hosted operating systems and the real scanner workflow on the hosted Linux runner or provisioned, trusted Windows/macOS runners with Java, Maven, Node, Docker Linux containers and Trivy available. Keep each platform JSON result as release evidence. A missing runner, failed check or missing artifact blocks release. Do not run untrusted pull-request code on self-hosted runners.

### ZIP scanner reports

Every archive includes ten individual normalized JSON reports under `scanner-reports/`, including disabled and failed scanners, plus `diagnostics/scanner-status.json`. Available Java XML and classpath diagnostics are retained under `diagnostics/`. Raw secret scanner output is never exported. Individual JSON reports use the same normalized findings as the consolidated HTML and JSON.

Acceptance runs retain validated positive and clean ZIP archives beside the JSON acceptance report in Downloads. Existing archives are never overwritten.

### Scanner result semantics

PASSED means completed analysis with a valid artifact and zero findings; FAILED means completed analysis with findings. ERROR means unreliable execution or normalization. DISABLED is intentional; SKIPPED identifies the documented no-Java-target condition. Coverage evidence is diagnostic, not a pass criterion. Local results remain advisory; CI enforcement is unchanged.

Run `python -m quality.Local_Scans.platform_acceptance` from the repository root to retain platform evidence in Downloads. The workflow defaults to Both (Linux and Windows concurrently), with independent jobs and no fail-fast cancellation. A single platform can also be selected. Windows and macOS real acceptance still require Linux-container Docker for TruffleHog; hosted Python regression is not a substitute.

The native launcher returns 2 for scanner execution errors after exporting the report; advisory findings alone return 0. Platform reports retain exit codes and elapsed time without arbitrary scanner stdout or stderr.

### Native TruffleHog acceptance

Local scans prefer a native `trufflehog` executable on PATH and retain Docker as a fallback. Windows acceptance uses a GitHub-hosted runner with native scanner binaries; Linux retains the Docker path. Windows package availability and real acceptance must be verified in Actions. Pylint uses a repository configuration only when present. Generated Python bytecode is excluded from Trivy scans.
