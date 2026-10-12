# Alignment Audit (Rules 85-100 / 16 items) — instruction-dsl-lint

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Static template linter, no security research content; Limits covers structural-lint misuse honestly. |
| 2 | Privacy/keys | PASS | No keys/tokens/real names; test fixtures use placeholder names only. |
| 3 | Copyright boundary | PASS | All DSL syntax and rule codes authored here; sim=none, no anchor repo text present; MIT LICENSE shipped. |
| 4 | Fact-check numbers | PASS | 40/40 checks measured, repro command given; ecosystem-adequacy claims marked [estimated]. |
| 5 | Confidence grading | PASS | README: High (85%) rule coverage, Medium (60%) design adequacy, each with a basis sentence. |
| 6 | Minimal Fallback | PASS | "Minimal Fallback (PLAN B)": two greps + acyclicity check in any language; JSON finding schema is the contract. |
| 7 | Quickstart timing | PASS | Quickstart labelled ~2 min, staged (self-test → single lint → CI wiring). |
| 8 | Conflict arbitration | PASS | "Design Trade-offs": sound rejections > zero dependencies > recall, with named rejections (no attribute access, depth cap). |
| 9 | Changelog ≥2 iterations | PASS | v0.1.0 → v0.1.1: E007 cycle bugfix, @var parser tightening, 29→40 tests, 2 test-expectation fixes. |
| 10 | Exemption (session rule) | N/A | Session-level governance item; static repo not applicable. |
| 11 | Knowledge cutoff | PASS | "no direct equivalent found as of 2026-10-11" dated in README why-not-X and FAQ. |
| 12 | Explicit assumptions | PASS | `[Core Assumptions]` lists 4 premises (plain-file templates, 3-construct sufficiency, union semantics, guaranteed termination). |
| 13 | Three-part self-test | PASS | functional (13) + error paths (10) + extreme edges (17) = 40/40 PASS. |
| 14 | Socratic FAQ | PASS | "When NOT to use this?" — programmatic templates, runtime assembly, injection-defense mis-expectation. |
| 15 | Pareto iteration | PASS | Round 2: test count +38% (29→40), 2 real detection bugs fixed (E007 unreachable, var parsing); CHANGELOG-traceable. |
| 16 | ≤60-word opening | PASS | First paragraph is 59 words ending with a judgment sentence ("fails the build instead of failing silently"). |

Additional: **Second-order effects** — "Limits & Second-order Effects" covers structure-not-semantics, template flattening pressure, dead-variable accumulation, and duplication-for-lint-cleanliness.
