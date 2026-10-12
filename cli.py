"""CLI for instruction-dsl-lint."""
import argparse
import json
import sys

import dslint


def main(argv=None):
    ap = argparse.ArgumentParser(prog="instruction-dsl-lint",
                                 description="Validate AI instruction templates written in the @var/{{ref}}/@include DSL.")
    ap.add_argument("paths", nargs="+", help="template files or directories")
    ap.add_argument("--max-depth", type=int, default=dslint.MAX_DEPTH,
                    help="include-chain depth limit (default 16)")
    ap.add_argument("--json", action="store_true", help="machine-readable report on stdout")
    args = ap.parse_args(argv)

    files = []
    for p in args.paths:
        import os
        if os.path.isdir(p):
            found = [os.path.join(p, f) for f in sorted(os.listdir(p))
                     if f.endswith((".itpl", ".txt", ".md"))]
            files.extend(found)
        elif os.path.exists(p):
            files.append(p)
        else:
            print("error: path not found: %s" % p, file=sys.stderr)
            return 2
    if not files:
        print("error: no templates found", file=sys.stderr)
        return 2

    rep = dslint.check_many(files, args.max_depth)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        for r in rep["reports"]:
            print("%-6s %s" % (r["verdict"], r["path"]))
            for f in r["findings"]:
                print("  %s L%s %s: %s" % (f["code"], f["line"], f["severity"], f["message"]))
        print("verdict: %s (%d file(s))" % (rep["verdict"], len(rep["reports"])))
    return dslint.verdict_exit(rep["verdict"])


if __name__ == "__main__":
    sys.exit(main())
