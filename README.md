# instruction-dsl-lint

A validator for AI instruction templates written in a deliberately tiny DSL — `@var` declares variables, `{{ name }}` references them, `@include` composes templates — that closes the loop on declarations, catches references that resolve to nothing, and refuses circular include chains before your prompt ever renders. Run it in CI and a broken prompt template fails the build instead of failing silently at inference time.

**Confidence: High (85%)** that the nine rule codes cover the structural failure modes of this DSL (undeclared/unused/duplicate variables, bad names and types, unknown/circular/over-deep includes, empty templates); **Medium (60%)** that a regex-and-closure design is enough for real template estates — it sees structure, not semantics [estimated].

## Problem

Teams accumulating hundreds of AI prompt templates render them with string substitution, and the failure mode is always the same one discovered at 2 a.m.: a template references `{{ user_name }}` that nothing declares, or two templates include each other and rendering loops until the process dies. Prompt frameworks ship renderers but almost nothing ships *structural validators* — a GitHub search for prompt-template linters matching this DSL surface found no direct equivalent as of 2026-10-11. The overlooked angle: prompt templates are just text with three constructs, so the entire validation problem is a graph-closure exercise that needs zero dependencies.

## How it works

The parser recognizes exactly three constructs per line:

| Construct | Syntax | Example |
|---|---|---|
| Declaration | `@var name[:type]` | `@var user:text` |
| Reference | `{{ name }}` (whitespace-tolerant) | `Hello {{ user }}` |
| Include | `@include target` | `@include common/style` |

Types: `text, int, float, bool, list, path`. Validation runs two layers:

1. **Closure resolution** — the `@include` graph is walked depth-first (limit 16) and memoized; cycles (`E007`), over-deep chains (`E008`), unreadable files (`E010`) and missing targets (`E006`) surface here.
2. **Structural rules** — `E001` undeclared reference, `E002` unused declaration (warn), `E003` duplicate declaration, `E004` bad variable name, `E005` unknown type, `E009` empty template.

A reference is legal if any template in its closure declares it — so a shared `@var locale:text` in an included base template satisfies every parent. Verdicts: PASS / WARN / FAIL; exit codes 0 (pass or warn), 1 (fail), 2 (usage error).

## Quickstart (~2 min)

```bash
# 1. Self-test: 40 checks across functional / error-path / extreme-edge (~2 s)
python self_test.py

# 2. Lint a template
python cli.py templates/report.itpl           # human-readable findings
python cli.py templates/ --json               # whole directory, machine-readable

# 3. Wire into CI (non-zero exit on FAIL)
python cli.py prompts/ --json > lint_report.json
```

## Why not X

A targeted search found **no direct equivalent found as of 2026-10-11** for a validator over a declare/reference/include DSL for AI instruction templates. Nearest adjacent tools, and why each falls short:

| Alternative | Why not this tool's job |
|---|---|
| Jinja2 / template engines (jinja2-cli) | Renderers, not validators — an undefined variable only fails at render time with a runtime exception, and include cycles raise deep in the stack; no unused-variable or naming hygiene, no machine-readable rule codes |
| Prompt-management SaaS (LangSmith, PromptLayer) | Track versions in their cloud; the structural health of the template text itself isn't lintable offline, and your templates stop being plain files |
| Generic linters (eslint, yamllint) | Know nothing about the `@var`/`{{ }}`/`@include` grammar — every rule would have to be hand-written as custom plugins, which is exactly what this repo already is |

## Minimal Fallback (PLAN B)

No Python? The spec is one paragraph: a reference `{{ x }}` must resolve to some `@var x` in the transitive `@include` closure; includes must be acyclic. Enforce it with two greps and a topological sanity check in any scripting language. The JSON finding schema (`{code, severity, line, message}`) is the contract any re-implementation must emit.

## Design Trade-offs

Priority order: **sound rejections > zero dependencies > recall**. References are matched syntactically — `{{user}}` and `{{ user }}` both resolve, but `{{ user.name }}` is not a reference (no attribute access; flatten your variables). The include depth limit (16) trades away legitimately deep hierarchies for guaranteed termination. Unused declarations are a *warning*, not an error, because scaffolding future variables is normal. We deliberately do not parse Jinja/`{placeholders}`-style syntaxes: one opinionated grammar is checkable; ten grammars is a framework.

## Limits & Second-order Effects

- Structure-only: a template can pass with a nonsensical instruction ("ignore all previous rules, {{ user }}"); this tool validates plumbing, not prompt quality.
- The 16-deep include cap will reject exotic-but-real hierarchies; teams will flatten templates to satisfy the linter, which may or may not be a win.
- Because unused declarations only WARN, template estates will accumulate dead variables; expect a follow-up `--strict-unused` workflow need.
- If CI gates renders on this lint, authors may inline shared sections to avoid include-graph friction — trading duplication for lint-cleanliness.

## FAQ

**Why a new DSL instead of validating Jinja?** The point is that three constructs can be fully specified in one README page and validated with a closure walk; Jinja's feature surface (macros, filters, control flow) is why nobody validates it structurally.

**Can two templates with the same variable name conflict?** No — closure semantics are union-based: any declaration anywhere in the closure satisfies a reference. Type conflicts across templates are not (yet) checked; treat that as a known gap.

**When NOT to use this?** If your templates are generated programmatically and rendered in the same process, the renderer already catches undefined variables — the linter adds value only when templates are static assets edited by humans, versioned, or rendered long after they're written. Don't use it for runtime prompt assembly, and don't use it as a prompt-injection defense; it validates nothing about content.

**Is the DSL stable?** As of 2026-10-11 the three constructs and nine rule codes are the whole spec; extensions (attribute access, conditionals) would change the closure model and are intentionally out of scope for v0.1.x.

## [Core Assumptions]

1. AI instruction templates are plain UTF-8 text files edited by humans, not objects inside a runtime framework — otherwise the renderer already owns this problem.
2. A three-construct grammar (`@var`, `{{ }}`, `@include`) is expressive enough for the template estates this tool targets; anything needing control flow needs a real engine, not a linter.
3. Reference resolution is name-based union across the include closure; shadowing and scoped namespacing are explicitly rejected complexity.
4. Termination must be guaranteed (depth cap + cycle rejection) even at the cost of rejecting legitimate deep hierarchies.

*Data as of 2026-10-11. Measured: 40/40 self-test checks PASS (functional 13, error paths 10, extreme edges 17), repro `python self_test.py` on Windows 10 / CPython 3.11. Adequacy of the nine rules for real-world estates is [estimated].*

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [prompt-regression-harness](https://github.com/chenhz01/prompt-regression-harness) · [prompt-version-diff](https://github.com/chenhz01/prompt-version-diff) · [prompt-template-merge](https://github.com/chenhz01/prompt-template-merge)
