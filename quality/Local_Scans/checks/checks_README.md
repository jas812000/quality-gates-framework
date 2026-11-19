# Local Scanner Wrappers

The Java scanners currently use POSIX shell wrappers:

- `check_checkstyle.sh` — Checkstyle
- `check_pmd.sh` — PMD
- `check_spotbugs.sh` — SpotBugs

Run them through the local launcher from the host repository root:

```sh
sh quality/Local_Scans/run-local-checks.sh
```

The launcher selects Python and discovers Maven modules containing Java source files in `src/main/java`, including multiple source-bearing modules. It passes the selected interpreter and module information to the Java execution layer. **Do not assume the host uses a `backend/` directory.** Optional explicit overrides can be supplied via the validated project configuration.

The Java wrappers require compatible Java and Maven tooling and may download scanner distributions. SpotBugs also needs compiled bytecode. The additional scanner orchestration uses Python scripts in this directory for Python, HTML, CSS, and secret scanning. Tools can fail because of missing dependencies, network access, malformed artifacts, or execution errors; such failures must not be presented as clean scans.

Scanner status is represented separately from findings. `CLEAN`, `FINDINGS`, `DISABLED`, and `ERROR` have different meanings. Local scans are advisory; CI enforcement is handled separately.

**Portability:** these shell wrappers do not provide native Windows execution. The current Windows batch entrypoint uses Git Bash. See [local scanning](../README.md) and [portability](../../PORTABILITY.md).
