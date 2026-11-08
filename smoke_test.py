#!/usr/bin/env python3
"""Execute every CS/DS 125 notebook and report what breaks.

Adapted from public/225/smoke_test.py. The static check, --clear and the
venv/kernel isolation are the same. Execution differs, because most 125
notebooks are exercises rather than finished teaching notebooks:

- Exercise cells are left blank (or half-written) for students, and some
  cells call input(). Running top to bottom therefore always produces some
  errors. Notebooks run with errors allowed, and every error is sorted into
  one of two groups:
    expected  NameError, SyntaxError, IndentationError and
              StdinNotImplementedError (input() has no keyboard here). These
              are what an unfinished exercise produces.
    check     anything else: a failed data download, a missing file, a
              pandas API change, an import error. These usually mean the
              notebook is broken for students too.
  A cell that raises on purpose (a demonstration of a TypeError, a "this
  code has a bug, fix it" prompt) carries the standard Jupyter cell tag
  "raises-exception"; its errors count as expected. A cell that must not run
  unattended at all (a deliberate infinite loop) carries "smoke-skip" and is
  replaced with `pass` in the temp copy. Tags are cell metadata, which Colab
  ignores.
  The exit status is non-zero only for "check" errors (or a static-check
  problem), so a clean run means "nothing broke that a student did not
  cause". It does not mean every cell ran.
- The committed notebooks are never modified; each run works on temp copies.
- Colab has wget and macOS usually doesn't, so `!wget URL` lines are
  rewritten to `!curl -sSLO URL` in the temp copy.

Usage:
    python smoke_test.py                  # static check, then execute everything
    python smoke_test.py 04 05_2          # only paths containing a pattern
    python smoke_test.py --counts         # static check only, no execution
    python smoke_test.py --clear          # clear outputs in place, no execution
    python smoke_test.py --list           # show what would run, don't run
    python smoke_test.py -v               # also list the expected errors
    python smoke_test.py --timeout 600    # per-notebook timeout in seconds
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent
VENV_DIR = ROOT / "venv"

EXCLUDE_DIR_PARTS = {"venv", ".ipynb_checkpoints", "_site"}


def venv_warning():
    """None if running from ./venv (or if no ./venv exists, as in CI);
    otherwise a banner to print.

    Jupyter picks a kernel via sys.prefix, which is set by which python ran
    this script, not by whether `source venv/bin/activate` was typed.
    (Checking sys.executable directly doesn't work: venv/bin/python3 is a
    symlink to the system interpreter, so resolving it collapses both paths
    to the same file. sys.prefix is what venvs actually redirect via
    pyvenv.cfg, so it's the correct signal.) If this process isn't running
    with ./venv's prefix, notebooks execute against whatever kernel is
    registered elsewhere on the machine, which can be missing or have
    outdated packages. Failures from that mismatch look exactly like real
    notebook bugs, so flag it loudly rather than let it masquerade as one.
    """
    if not VENV_DIR.exists():
        return None  # CI installs into its own interpreter; nothing to compare
    try:
        running = pathlib.Path(sys.prefix).resolve()
        expected = VENV_DIR.resolve()
    except OSError:
        return None
    if running == expected:
        return None
    return (
        "\n"
        "############################################################\n"
        "#  WARNING: not running from this project's venv.\n"
        f"#  Expected prefix: {expected}\n"
        f"#  Actual prefix:   {running}\n"
        "#  Run `source venv/bin/activate` first. Otherwise notebooks\n"
        "#  execute against whatever Jupyter kernel is registered\n"
        "#  elsewhere, and failures below may be environment artifacts,\n"
        "#  not real bugs.\n"
        "############################################################\n"
    )


def collect(patterns):
    nbs = []
    for p in sorted(ROOT.rglob("*.ipynb")):
        rel = p.relative_to(ROOT)
        if EXCLUDE_DIR_PARTS & set(rel.parts):
            continue
        if patterns and not any(pat in str(rel) for pat in patterns):
            continue
        nbs.append(rel)
    return nbs


def check_saved_state(nbs):
    """Verify each notebook's committed state is fully cleared.

    Returns a list of problem strings (empty means all clean): every code
    cell must have execution_count = null and an empty outputs list.
    Students open these notebooks in Colab and run each cell themselves, so
    a saved output would show them a result they were meant to produce.
    """
    problems = []
    for rel in nbs:
        nb = json.loads((ROOT / rel).read_text())
        for i, c in enumerate(nb["cells"]):
            if c["cell_type"] != "code":
                continue
            if c.get("execution_count") is not None:
                problems.append(
                    f"{rel}: code cell {i} has a saved execution_count ({c['execution_count']})"
                )
            if c.get("outputs"):
                problems.append(f"{rel}: code cell {i} has saved output(s)")
    return problems


# Cell metadata that only makes sense alongside a saved output (execution
# timestamps, Colab's output-rendering hints) and goes stale the moment the
# output it describes is cleared.
OUTPUT_ONLY_METADATA_KEYS = {"execution", "outputId", "colab"}


def _detect_format(raw, nb):
    """Reverse-engineer the (indent, sort_keys, trailing_newline) a notebook
    was last saved with, by brute-forcing json.dumps against the raw text.

    Notebooks in this repo were saved by a mix of tools/versions (classic
    Jupyter, Colab exports, ...) and are not all serialized the same way
    (some 1-space indent, some 2; some with sorted keys, some insertion
    order; some with a trailing newline, some without). Guessing wrong
    would rewrite a whole file's formatting on a one-line content edit and
    bury the real diff in noise, so every write reuses whatever format the
    file already had rather than imposing one convention.
    """
    for indent in (1, 2):
        for sort_keys in (True, False):
            for trailing_newline in (True, False):
                dumped = json.dumps(nb, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
                if trailing_newline:
                    dumped += "\n"
                if dumped == raw:
                    return indent, sort_keys, trailing_newline
    return None


def _write_notebook(path, nb, fmt):
    indent, sort_keys, trailing_newline = fmt
    dumped = json.dumps(nb, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    if trailing_newline:
        dumped += "\n"
    path.write_text(dumped)


def clear_outputs(nbs):
    """Reset every code cell to execution_count = null, outputs = [] in place.

    Also strips per-cell metadata that only described the now-removed output
    (execution timestamps, Colab's outputId/base_uri/height hints). Reuses
    each file's own existing JSON formatting (see _detect_format) so a
    clear-only pass produces a minimal diff.
    """
    changed_count = 0
    unrecognized = []
    for rel in nbs:
        path = ROOT / rel
        raw = path.read_text()
        nb = json.loads(raw)
        fmt = _detect_format(raw, nb)
        if fmt is None:
            unrecognized.append(rel)
            fmt = (1, True, True)  # nbformat's own default; best effort
        changed = False
        for c in nb["cells"]:
            if c["cell_type"] != "code":
                continue
            if c.get("execution_count") is not None:
                c["execution_count"] = None
                changed = True
            if c.get("outputs"):
                c["outputs"] = []
                changed = True
            meta = c.get("metadata", {})
            for key in OUTPUT_ONLY_METADATA_KEYS & meta.keys():
                del meta[key]
                changed = True
        if changed:
            _write_notebook(path, nb, fmt)
            changed_count += 1
    print(f"Cleared {changed_count}/{len(nbs)} notebook(s)"
          f" ({len(nbs) - changed_count} already clean).")
    if unrecognized:
        print("Could not recognize the existing JSON formatting for "
              f"{len(unrecognized)} notebook(s); wrote nbformat's default "
              "format instead, so their diff may be larger than necessary:")
        for rel in unrecognized:
            print(f"  {rel}")
    return 0


EXPECTED_ERRORS = {"NameError", "SyntaxError", "IndentationError", "StdinNotImplementedError"}


def prepare_copy(src_text):
    """Notebook text for the temp copy: curl for wget, skipped cells."""
    nb = json.loads(src_text)
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        tags = c.get("metadata", {}).get("tags", [])
        if "smoke-skip" in tags:
            c["source"] = "pass  # smoke-skip"
            continue
        src = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
        c["source"] = re.sub(r"!\s*wget\s+(-\S+\s+)*", "!curl -sSLO ", src)
    return json.dumps(nb)


def cell_errors(executed_path):
    """[(cell index, ename, evalue)] for every error output in an executed notebook.

    Errors from cells tagged raises-exception are reported with ename
    prefixed "(tagged) ", which is not in any error class, so callers treat
    them as expected via is_expected().
    """
    nb = json.loads(executed_path.read_text())
    errs = []
    for i, c in enumerate(nb["cells"]):
        tagged = "raises-exception" in c.get("metadata", {}).get("tags", [])
        for out in c.get("outputs", []):
            if out.get("output_type") == "error":
                errs.append((i, ("(tagged) " if tagged else "") + out.get("ename", "?"), (out.get("evalue") or "").splitlines()[0][:160] if out.get("evalue") else ""))
    return errs


def is_expected(ename):
    return ename.startswith("(tagged) ") or ename in EXPECTED_ERRORS


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("patterns", nargs="*",
                    help="only check notebooks whose path contains one of these substrings")
    ap.add_argument("--list", action="store_true",
                    help="list notebooks that would run, then exit")
    ap.add_argument("--counts", action="store_true",
                    help="run only the static saved-state check, no execution")
    ap.add_argument("--clear", action="store_true",
                    help="clear outputs/execution_count in place, no execution")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="also list expected (unfinished-exercise) errors")
    ap.add_argument("--timeout", type=int, default=300,
                    help="per-notebook timeout in seconds (default 300)")
    args = ap.parse_args()

    nbs = collect(args.patterns)
    if not nbs:
        print("No notebooks matched.")
        return 1
    if args.list:
        for nb in nbs:
            print(nb)
        print(f"\n{len(nbs)} notebooks")
        return 0

    if args.clear:
        return clear_outputs(nbs)

    problems = check_saved_state(nbs)
    if problems:
        print(f"Static check: {len(problems)} problem(s) in saved notebook state:")
        for p in problems:
            print(f"  {p}")
        print("\nClear outputs before committing, e.g.:")
        print("  python smoke_test.py --clear <notebook>")
    else:
        print(f"Static check: all {len(nbs)} notebooks have clean saved state.")
    if args.counts:
        return 1 if problems else 0

    warning = venv_warning()
    if warning:
        print(warning)

    flagged = []   # (nb, [errors]) with at least one "check" error, or a crash
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        # See public/225/smoke_test.py for why nbconvert runs as
        # `sys.executable -m nbconvert` with an empty JUPYTER_DATA_DIR.
        env = dict(os.environ, JUPYTER_DATA_DIR=str(tmp / "jupyter_data"))
        for i, nb in enumerate(nbs, 1):
            print(f"[{i}/{len(nbs)}] {nb} ... ", end="", flush=True)
            start = time.time()
            work_dir = tmp / str(nb).replace("/", "__")
            work_dir.mkdir()
            nb_copy = work_dir / nb.name
            nb_copy.write_text(prepare_copy((ROOT / nb).read_text()))
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "nbconvert", "--to", "notebook",
                     "--execute", "--allow-errors", str(nb_copy),
                     "--output", "executed", "--output-dir", str(work_dir),
                     "--ExecutePreprocessor.timeout", str(args.timeout)],
                    capture_output=True, text=True, timeout=args.timeout + 60, env=env,
                )
                crash = None if proc.returncode == 0 else proc.stderr
            except subprocess.TimeoutExpired:
                crash = f"hard timeout after {args.timeout}s"
            elapsed = time.time() - start
            if crash:
                print(f"CRASH ({elapsed:.0f}s)")
                tail = "\n".join(l for l in crash.splitlines() if l.strip())[-1500:]
                flagged.append((nb, [(None, "CRASH", tail)]))
                continue
            errs = cell_errors(work_dir / "executed.ipynb")
            check = [e for e in errs if not is_expected(e[1])]
            expected = [e for e in errs if is_expected(e[1])]
            status = "ok" if not check else f"CHECK {len(check)}"
            print(f"{status} ({len(expected)} expected) ({elapsed:.0f}s)")
            if args.verbose:
                for c, en, ev in expected:
                    print(f"      cell {c}: {en}: {ev}")
            if check:
                flagged.append((nb, check))

    print(f"\n{len(nbs) - len(flagged)}/{len(nbs)} notebooks had no unexpected errors.")
    for nb, errs in flagged:
        print(f"\n=== {nb} ===")
        for c, en, ev in errs:
            print(f"  cell {c}: {en}: {ev}" if c is not None else f"  {en}: {ev}")
    if flagged and warning:
        print(warning)
    return 1 if (flagged or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
