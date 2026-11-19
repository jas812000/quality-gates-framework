# Optional Git Pre-Commit Hook

The framework includes `quality/Local_Scans/hooks/pre-commit`. Installing this hook is **optional**; copying the `quality/` directory does not automatically enable it.

From the consuming repository root on macOS/Linux:

```sh
git config core.hooksPath quality/Local_Scans/hooks
```

This changes the repository-local Git hooks path. **Check for existing hooks before enabling it:** replacing `core.hooksPath` may prevent other hooks from running. The hook runs `quality/Local_Scans/run-local-checks.sh`, reports errors, and **always exits successfully** so findings or scanner failures do not block commits. It is not a security enforcement boundary; CI policy enforcement must be configured separately.

To inspect the setting:

```sh
git config --local --get core.hooksPath
```

To remove this custom setting (only if you intend to restore Git's default hook location):

```sh
git config --local --unset core.hooksPath
```

The hook uses a POSIX shell and does not provide native Windows scanning. No `quality/project.json` is required for supported Maven layouts; optional configuration is documented in [PORTABILITY.md](../../PORTABILITY.md). See [local scanning](../README.md).
