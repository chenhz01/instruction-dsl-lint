# Changelog

## [0.1.1] - 2026-10-11

### Changed (round-2 iteration after first-draft self-audit)

- **Correctness:** fixed a real bug the first run exposed — circular `@include` detection (E007) could never fire because the closure memo check ran before the on-stack check, so `A→B→A` and self-includes silently passed as diamonds; stack membership is now tested first (2-cycle and self-include tests went FAIL→PASS).
- **Correctness:** the `@var` parser was tightened. The first loose token capture swallowed `name:type` into a single name (making `@var user:text` produce E004 noise and miss the real declaration); tokens are now partitioned on the first colon, so bad names (`9lives`, bare `@var`) correctly reach E004 and typed declarations parse.
- **Test rigor (+38%):** suite grew 29 → 40 checks; two first-draft expectations were themselves wrong (a malformed `{{ x and {{ y }}` case expected no findings although the inner `{{ y }}` is legitimately a reference; an unclosed-brace case expected the wrong verdict) — both rewritten to assert actual spec behavior. Added CLI exit-code, JSON-report-shape, WARN-aggregation and closure-resolution tests.
- **Docs:** README why-not-X section now states the no-equivalent finding with its as-of date.

## [0.1.0] - 2026-10-11

### Added

- `dslint.py`: parser for the 3-construct DSL (`@var name:type`, `{{ name }}`, `@include target`), transitive include-closure loader with memoization, 9 rule codes (E001–E010 minus E-off gaps), PASS/WARN/FAIL verdicts, batch mode, exit-code mapping.
- `cli.py`: file-or-directory linting, `--max-depth`, `--json` machine-readable reports; exit codes 0/1/2.
- `self_test.py`: three families — functional, error paths, extreme edges (100KB templates, 20k refs on one line, 20-deep include chains, unicode names, CRLF, binary garbage).
- MIT LICENSE (zhengming contributors), README, initial ALIGNMENT audit.
