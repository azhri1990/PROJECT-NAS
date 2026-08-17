# PROJECT-NAS `certify`

`runtime/project-nas.sh certify` is the local, deterministic certification entry point.

It checks repository/runtime invariants, executes the regression suite, validates Python compilation and shell syntax, runs doctor diagnostics, and confirms the live local runtime endpoints when they are available.

The command does not require paid APIs, hosted model credits, or cloud AI services.
