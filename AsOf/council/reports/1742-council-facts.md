VERDICT: PASS

1. No blocking findings. `uv run pytest -q tests/engine tests/pipeline` gave 140 passed, and that includes the 17 hidden cases. C17 (`drl.aero`) now returns `cannot_resolve` with missing "a domain that matches exactly one company" and a "Not a negative finding." evidence request.
2. `clear delhivery.com` in replay (temp ASOF_STATE_DIR) gives 5 attested lines, each with a point date and an Evidence id (E2..E6). The labels are correct: existence and listing "as recorded", headcount "profile-derived count", revenue_band "estimate", domains "true at retrieval only". Cost is credits 0.0, recorded 2.2 credits, ₹62.12. The cost_note matches README.md:60 and docs/demo.md:51-52 word for word.
3. Grep for "was true on" finds it only in negation or test contexts: README.md:23, tests/engine/test_guards.py:86 (an injected-domain test), tests/e2e/test_mcp_stdio.py:39 (an assertion that it is absent), and the docs, spec and agent files. No output or engine code produces it. Every statement uses the "Data point dated P states X; stored copy retrieved T." template.
4. Minor, not blocking: the delhivery.com entity lists `drl.aero` in `domains`. It is the record's `all_domains` and is labelled "true at retrieval only". README.md:111 says an alias is no longer treated as proof, and the listing is consistent with that.
5. Not re-run this round: the 6 hand-recomputed hidden cases (item 2 of the original brief) and the full `tests` run (only engine and pipeline were run). I did not diff 98856cc..HEAD.

FAILING TESTS: none (140 passed, tests/engine and tests/pipeline)
