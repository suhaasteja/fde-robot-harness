# demo-fixture baseline — do not edit during a demo

The known-good *vulnerable* state of `demo-fixture/`, restored by `bin/demo reset`.

This exists as a directory rather than a git ref because the pipeline mutates
`main`: a remediation PR that gets merged changes the fixture on the branch we
would otherwise reset from, so "restore from HEAD" quietly stops restoring the
vulnerability. Nothing here is ever patched by the pipeline, so a reset is exact
however many times the demo has run.

`middleware.js` here is deliberately vulnerable to CVE-2025-29927. Its test suite
should show one failing security test — that failure *is* the vulnerability.
