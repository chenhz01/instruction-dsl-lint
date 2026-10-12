"""instruction-dsl-lint: a tiny DSL for AI instruction templates plus a validator.

DSL surface (per template file, UTF-8 text):
  @var name:type      declare a variable (type optional, default "text")
  {{ name }}          reference a variable (braces may hug the name)
  @include target     include another template (resolved relative to this file)

Validation closures: a reference is legal if it resolves to a declaration in
the template itself or in any template reachable via @include (no cycles).
"""
from __future__ import annotations

import os
import re
import json

TYPES = {"text", "int", "float", "bool", "list", "path"}
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VAR_RE = re.compile(r"^\s*@var\s+(.+?)\s*$")
VAR_BARE_RE = re.compile(r"^\s*@var\s*$")
INC_RE = re.compile(r"^\s*@include\s+(\S+)\s*$")
REF_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
MAX_DEPTH = 16

SEV_ORDER = {"error": 2, "warn": 1}


def parse_template(text: str) -> dict:
    """Parse template text into declarations, references, includes."""
    decls, refs, includes = [], [], []
    for i, line in enumerate(text.splitlines(), 1):
        if VAR_BARE_RE.match(line):
            decls.append({"name": "", "type": "text", "line": i})
            continue
        m = VAR_RE.match(line)
        if m:
            token = m.group(1)
            name, _, ty = token.partition(":")
            decls.append({"name": name.strip(), "type": ty.strip() or "text", "line": i})
            continue
        m = INC_RE.match(line)
        if m:
            includes.append({"target": m.group(1), "line": i})
            continue
        for m in REF_RE.finditer(line):
            refs.append({"name": m.group(1), "line": i})
    return {"decls": decls, "refs": refs, "includes": includes}


def read_template(path: str) -> str:
    """Read a template; raise ValueError on undecodable bytes."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("not valid utf-8: %s" % e)


def resolve_include(base_dir: str, target: str) -> str:
    """Resolve an @include target relative to the including template's dir."""
    cand = target if os.path.isabs(target) else os.path.join(base_dir, target)
    if os.path.isdir(cand):
        raise FileNotFoundError("include target is a directory: %s" % target)
    if not os.path.exists(cand) and not os.path.exists(cand + ".itpl"):
        raise FileNotFoundError("include target not found: %s" % target)
    if os.path.exists(cand + ".itpl") and not os.path.exists(cand):
        cand = cand + ".itpl"
    return os.path.normpath(cand)


def load_closure(path: str, max_depth: int = MAX_DEPTH):
    """DFS the @include graph. Returns (closure dict, findings).
    closure maps normalized path -> parsed template (or None if unreadable).
    Findings include cycle (E007) and depth (E008) and unreadable (E010)."""
    findings, closure, stack = [], {}, []

    def walk(p: str):
        norm = os.path.normpath(os.path.abspath(p))
        if norm in stack:
            chain = " -> ".join(os.path.basename(s) for s in stack + [norm])
            findings.append({"code": "E007", "severity": "error", "line": 0,
                             "message": "circular include chain: %s" % chain})
            return
        if norm in closure:
            return
        if len(stack) >= max_depth:
            findings.append({"code": "E008", "severity": "error", "line": 0,
                             "message": "include depth limit %d exceeded" % max_depth})
            return
        try:
            text = read_template(p)
        except (OSError, ValueError) as e:
            findings.append({"code": "E010", "severity": "error", "line": 0,
                             "message": "cannot read template %s: %s" % (p, e)})
            return
        parsed = parse_template(text)
        closure[norm] = parsed
        stack.append(norm)
        base = os.path.dirname(p)
        for inc in parsed["includes"]:
            try:
                child = resolve_include(base, inc["target"])
            except FileNotFoundError as e:
                findings.append({"code": "E006", "severity": "error", "line": inc["line"],
                                 "message": str(e)})
                continue
            walk(child)
        stack.pop()

    walk(path)
    return closure, findings


def validate_template(text: str, closure: dict, root_path: str) -> list:
    """Structural checks for one template against its include closure."""
    findings = []
    parsed = parse_template(text)
    seen, dup = set(), set()
    for d in parsed["decls"]:
        if d["name"] in seen:
            dup.add(d["name"])
        seen.add(d["name"])
        if not NAME_RE.match(d["name"]):
            findings.append({"code": "E004", "severity": "error", "line": d["line"],
                             "message": "bad variable name '%s'" % d["name"]})
        if d["type"] not in TYPES:
            findings.append({"code": "E005", "severity": "error", "line": d["line"],
                             "message": "unknown type '%s' for variable '%s' (valid: %s)"
                                        % (d["type"], d["name"], ",".join(sorted(TYPES)))})
    for d in parsed["decls"]:
        if d["name"] in dup:
            findings.append({"code": "E003", "severity": "error", "line": d["line"],
                             "message": "duplicate declaration of '%s'" % d["name"]})

    closure_names = set()
    for norm, cparse in closure.items():
        if cparse:
            closure_names |= {d["name"] for d in cparse["decls"]}

    ref_names = set()
    for r in parsed["refs"]:
        ref_names.add(r["name"])
        if r["name"] not in closure_names:
            findings.append({"code": "E001", "severity": "error", "line": r["line"],
                             "message": "undeclared variable '%s'" % r["name"]})
    for d in parsed["decls"]:
        if d["name"] not in ref_names:
            findings.append({"code": "E002", "severity": "warn", "line": d["line"],
                             "message": "declared variable '%s' is never referenced" % d["name"]})

    if not text.strip():
        findings.append({"code": "E009", "severity": "warn", "line": 0,
                         "message": "template is empty"})
    return findings


def check_path(path: str, max_depth: int = MAX_DEPTH) -> dict:
    """Full check of one template file: closure + structural findings + verdict."""
    findings = []
    try:
        text = read_template(path)
    except (OSError, ValueError) as e:
        return {"path": path, "findings": [{"code": "E010", "severity": "error",
                                            "line": 0, "message": str(e)}],
                "verdict": "FAIL"}
    closure, clo_findings = load_closure(path, max_depth)
    findings += clo_findings
    findings += validate_template(text, closure, path)
    sev = max([SEV_ORDER[f["severity"]] for f in findings], default=0)
    verdict = {0: "PASS", 1: "WARN", 2: "FAIL"}[sev]
    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["line"]))
    return {"path": path, "findings": findings, "verdict": verdict}


def check_many(paths: list, max_depth: int = MAX_DEPTH) -> dict:
    reports = [check_path(p, max_depth) for p in paths]
    failed = [r["path"] for r in reports if r["verdict"] == "FAIL"]
    return {"reports": reports, "failed": failed,
            "verdict": "FAIL" if failed else "WARN" if any(r["verdict"] == "WARN" for r in reports) else "PASS"}


def verdict_exit(verdict: str) -> int:
    return {"PASS": 0, "WARN": 0, "FAIL": 1}.get(verdict, 2)
