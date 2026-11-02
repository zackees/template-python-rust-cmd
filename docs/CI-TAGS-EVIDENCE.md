# CI tag evidence

This experiment continues zackees/ci.yml#46 on the current template workflow.
The original draft's empty log supplies no completed tag-case evidence.
The linter and workflow pins remain those selected by current main.

## Cases and required observations

Run the cases in the following order by changing this draft PR's title.
For each completed run, record its source SHA, event title, run URL, selected
platform build/run jobs, required suites, final CI result and reuse decisions.
Use the actual hosted jobs and logs to verify selection and execution.

| Case | Required observation | Status |
| --- | --- | --- |
| `[ci-windows]` | Windows group builds and native execution; ordinary fast coverage retained | Pending |
| `[ci-macos]` | macOS group builds and native execution; ordinary fast coverage retained | Pending |
| `[ci-linux]` | Linux group selection and execution; ordinary fast coverage retained | Pending |
| `[ci-perf][no-test]` | Build and performance execution; ordinary test suites omitted; merge gate refuses the incomplete coverage selection | Pending |

The perf-only case is an intentional merge-gate rejection. Record that result
without marking the PR ready to merge. After recording every case, restore a
normal title and require its ordinary checks before merging this evidence log.
Do not infer OS-group coverage from a release run or from planned matrix output.

## Results

No resumed experiment case has completed yet. Native release qualification in
#59 and #60 is separate from these title-selection cases. Final run evidence
will replace each Pending entry as the original workflow executes it.
