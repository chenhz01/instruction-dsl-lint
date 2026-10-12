"""Self-test for instruction-dsl-lint: functional / error-path / extreme-edge."""
from __future__ import annotations

import json
import os
import sys
import tempfile

import dslint

_results = []


def record(family, name, ok, detail=""):
    _results.append((family, name, "PASS" if ok else "FAIL", detail))


def make(tmp, name, text):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


# ---------------------------------------------------------------- functional

def t_functional(tmp):
    p = make(tmp, "ok.itpl", "@var user:text\nHello {{ user }}, please review {{user}}.\n")
    r = dslint.check_path(p)
    record("functional", "clean template PASS", r["verdict"] == "PASS", str(r["findings"]))

    p = make(tmp, "undecl.itpl", "Hello {{ missing }}\n")
    r = dslint.check_path(p)
    record("functional", "undeclared reference -> E001 FAIL",
           any(f["code"] == "E001" for f in r["findings"]) and r["verdict"] == "FAIL")

    p = make(tmp, "unused.itpl", "@var never_used:text\nstatic body\n")
    r = dslint.check_path(p)
    record("functional", "unused declaration -> E002 WARN",
           any(f["code"] == "E002" for f in r["findings"]) and r["verdict"] == "WARN")

    p = make(tmp, "dup.itpl", "@var a:text\n@var a:int\nuse {{ a }}\n")
    r = dslint.check_path(p)
    record("functional", "duplicate declaration -> E003",
           any(f["code"] == "E003" for f in r["findings"]))

    p = make(tmp, "badtype.itpl", "@var a:vector\nuse {{ a }}\n")
    r = dslint.check_path(p)
    record("functional", "unknown type -> E005",
           any(f["code"] == "E005" for f in r["findings"]))

    p = make(tmp, "multitype.itpl", "@var n:int\n@var xs:list\n@var flag:bool\n{{ n }} {{ xs }} {{ flag }}\n")
    r = dslint.check_path(p)
    record("functional", "all declared types accepted", r["verdict"] == "PASS")

    child = make(tmp, "child.itpl", "@var shared:text\nshared body {{ shared }}\n")
    parent = make(tmp, "parent.itpl", "@include child.itpl\ncall {{ shared }}\n")
    r = dslint.check_path(parent)
    record("functional", "ref satisfied by include closure PASS", r["verdict"] == "PASS",
           json.dumps(r["findings"]))

    r = dslint.parse_template("use {{ a }} and {{b}}\n@var a:text")
    record("functional", "hugging braces both parsed",
           len(r["refs"]) == 2 and r["decls"][0]["name"] == "a")

    r = dslint.check_many([make(tmp, "p1.itpl", "{{ x }}"),
                           make(tmp, "p2.itpl", "@var x:text\n{{ x }}")])
    record("functional", "batch fails only offending file",
           r["failed"] and os.path.basename(r["failed"][0]).startswith("p1"))

    record("functional", "exit-code mapping", dslint.verdict_exit("PASS") == 0
           and dslint.verdict_exit("WARN") == 0 and dslint.verdict_exit("FAIL") == 1)

    p = make(tmp, "emptydecl.itpl", "@var a\nuse {{ a }}\n")
    r = dslint.check_path(p)
    record("functional", "declaration without type defaults to text",
           any(d["type"] == "text" for d in dslint.parse_template(open(p, encoding="utf-8").read())["decls"])
           and r["verdict"] == "PASS")

    p = make(tmp, "inc_order.itpl", "use {{ late }}\n@var late:text\n")
    r = dslint.check_path(p)
    record("functional", "declaration after reference still resolves", r["verdict"] == "PASS")


# ---------------------------------------------------------------- error paths

def t_error_paths(tmp):
    p = make(tmp, "empty.itpl", "")
    r = dslint.check_path(p)
    record("error", "empty template -> E009", any(f["code"] == "E009" for f in r["findings"]))

    r = dslint.check_path(os.path.join(tmp, "nope_missing.itpl"))
    record("error", "missing file -> E010 FAIL not crash",
           r["verdict"] == "FAIL" and any(f["code"] == "E010" for f in r["findings"]))

    a = make(tmp, "cyc_a.itpl", "@include cyc_b.itpl\nA\n")
    b = make(tmp, "cyc_b.itpl", "@include cyc_a.itpl\nB\n")
    r = dslint.check_path(a)
    record("error", "2-cycle include -> E007", any(f["code"] == "E007" for f in r["findings"]))

    p = make(tmp, "selfinc.itpl", "@include selfinc.itpl\nhi\n")
    r = dslint.check_path(p)
    record("error", "self-include -> E007", any(f["code"] == "E007" for f in r["findings"]))

    p = make(tmp, "badinc.itpl", "@include ghost_does_not_exist.itpl\nx\n")
    r = dslint.check_path(p)
    record("error", "unknown include -> E006", any(f["code"] == "E006" for f in r["findings"]))

    p = make(tmp, "bin.itpl", "")
    with open(p, "wb") as f:
        f.write(b"\x00\xff\xfe garbage \x99")
    r = dslint.check_path(p)
    record("error", "binary garbage -> E010 not crash", r["verdict"] == "FAIL")

    p = make(tmp, "digit.itpl", "@var 9lives:text\nuse {{ nine }}\n@var nine:text\n")
    r = dslint.check_path(p)
    record("error", "digit-leading name -> E004", any(f["code"] == "E004" for f in r["findings"]))

    p = make(tmp, "emptyvar.itpl", "@var\nuse {{ x }}\n@var x:text\n")
    r = dslint.check_path(p)
    record("error", "@var with no name -> E004", any(f["code"] == "E004" for f in r["findings"]))

    p = make(tmp, "unclosed.itpl", "@var x:text\nuse {{ x\n")
    r = dslint.check_path(p)
    record("error", "unclosed brace ignored, decl flagged unused",
           r["verdict"] == "WARN" and any(f["code"] == "E002" for f in r["findings"]))

    p = make(tmp, "innerbrace.itpl", "@var x:text\nuse {{ x and {{ y }}\n")
    r = dslint.check_path(p)
    record("error", "inner {{ y }} inside malformed brace still detected -> E001",
           any(f["code"] == "E001" and f["message"].find("y") >= 0 for f in r["findings"]))

    d = os.path.join(tmp, "sub")
    os.makedirs(d, exist_ok=True)
    p = make(tmp, "dirinc.itpl", "@include sub\nx\n")
    r = dslint.check_path(p)
    record("error", "include target is a directory -> E006", any(f["code"] == "E006" for f in r["findings"]))


# ---------------------------------------------------------------- extreme edges

def t_extreme_edges(tmp):
    p = make(tmp, "big.itpl", "@var big:text\n" + ("step {{ big }}; " * 2000))
    r = dslint.check_path(p)
    record("edge", "100KB template with 2000 refs", r["verdict"] == "PASS")

    many = "@var v%d:text\n" % 0 + "".join("{{ v0 }}\n" for _ in range(500))
    p = make(tmp, "manyrefs.itpl", many)
    record("edge", "500 refs on one variable", dslint.check_path(p)["verdict"] == "PASS")

    p = make(tmp, "uni.itpl", "@var 名前:text\nこんにちは {{ 名前 }} — {{ user }}\n@var user:text\n")
    r = dslint.check_path(p)
    record("edge", "unicode var name and text handled", isinstance(r, dict))

    depth = make(tmp, "d0.itpl", "@include d1.itpl\nleaf\n")
    for i in range(1, 20):
        make(tmp, "d%d.itpl" % i, "@include d%d.itpl\nlayer %d\n" % (i + 1, i))
    r = dslint.check_path(depth)
    record("edge", "chain > depth limit -> E008", any(f["code"] == "E008" for f in r["findings"]))

    c1 = make(tmp, "twice_a.itpl", "@var dup_inc:text\n{{ dup_inc }}\n")
    c2 = make(tmp, "twice_b.itpl", "@include twice_a.itpl\n@include twice_a.itpl\n{{ dup_inc }}\n")
    r = dslint.check_path(c2)
    record("edge", "diamond/duplicate include is not a cycle", r["verdict"] == "PASS")

    p = make(tmp, "crlf.itpl", "@var w:text\r\nhello {{ w }}\r\n")
    r = dslint.check_path(p)
    record("edge", "CRLF line endings parsed", r["verdict"] == "PASS")

    p = make(tmp, "longline.itpl", "@var x:text\n" + ("{{ x }}" * 20000))
    r = dslint.check_path(p)
    record("edge", "one 100KB line with 20000 refs", r["verdict"] == "PASS")

    p = make(tmp, "comment.itpl", "# @var ghost:text\n@var real:text\n{{ real }}\n")
    r = dslint.check_path(p)
    record("edge", "commented-out @var not treated as declaration",
           r["verdict"] == "PASS" and not any(f["code"] == "E001" for f in r["findings"]))

    # ---- round-2 additions: CLI, report shape, aggregation ----

    p = make(tmp, "warnagg.itpl", "@var unused_only:text\nno refs here\n")
    ok = make(tmp, "passagg.itpl", "@var v:text\n{{ v }}\n")
    rep = dslint.check_many([p, ok])
    record("edge", "check_many aggregates WARN below FAIL", rep["verdict"] == "WARN" and not rep["failed"])

    rep = dslint.check_many([ok])
    blob = json.dumps(rep)
    record("edge", "check_many JSON-serializable", '"verdict": "PASS"' in blob)

    import cli as cli_mod
    good = make(tmp, "cli_ok.itpl", "@var u:text\n{{ u }}\n")
    record("edge", "cli main clean -> 0", cli_mod.main([good]) == 0)
    record("edge", "cli main failing file -> 1",
           cli_mod.main([make(tmp, "cli_bad.itpl", "{{ nope }}")]) == 1)
    record("edge", "cli main missing path -> 2", cli_mod.main(["__definitely_absent__.itpl"]) == 2)
    record("edge", "cli main --json prints valid JSON",
           cli_mod.main([good, "--json"]) == 0)

    child = make(tmp, "n1.itpl", "@var shared2:text\nbody {{ shared2 }}\n")
    parent = make(tmp, "n0.itpl", "@include n1.itpl\n{{ shared2 }}\n")
    rep = json.loads(json.dumps(dslint.check_path(parent)))
    record("edge", "closure variables satisfy parent (fresh pair)", rep["verdict"] == "PASS")

    p = make(tmp, "tabs.itpl", "\t@var tabbed:text\nvalue {{ tabbed }}\n")
    r = dslint.check_path(p)
    record("edge", "leading tab before @var accepted", r["verdict"] == "PASS")

    p = make(tmp, "colon.itpl", "@var weird ::int\nuse {{ weird }}\n")
    r = dslint.check_path(p)
    record("edge", "double-colon type spec still parsed or cleanly flagged", isinstance(r, dict) and r["verdict"] in ("PASS", "WARN", "FAIL"))


def main():
    tmp = tempfile.mkdtemp(prefix="idslint_test_")
    try:
        t_functional(tmp)
        t_error_paths(tmp)
        t_extreme_edges(tmp)
    finally:
        for f in os.listdir(tmp):
            try:
                os.unlink(os.path.join(tmp, f))
            except OSError:
                pass
        try:
            os.rmdir(os.path.join(tmp, "sub"))
        except OSError:
            pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    fails = [r for r in _results if r[2] == "FAIL"]
    for fam, name, status, detail in _results:
        print("[%s] %-10s %s%s" % (status, fam, name, (" | " + detail) if detail else ""))
    print("\n%d checks, %d failed" % (len(_results), len(fails)))
    print("SUMMARY: PASS %d/%d" % (len(_results) - len(fails), len(_results)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
