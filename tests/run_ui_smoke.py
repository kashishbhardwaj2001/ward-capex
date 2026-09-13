"""
Drive every interaction in docs/index.html with a real browser and assert it works.

WHY THIS EXISTS. The atlas is a single static file with no framework, so nothing type-checks
it and no test runner knows about it. Two classes of bug got all the way to a published page
before this existed, and neither would be caught by looking at a screenshot:

  * Two charts were accidentally nested inside the table's click handler, so they rendered
    empty until a reader clicked a row. The DOM had the containers; they were just blank.
  * The map had only a click handler while CSS changed the stroke on :hover - so the page
    advertised interactivity it did not have, and hovering 198 wards did nothing.

A third was caught by this harness on its first run: the validation ladder was rendering
198 ward rows instead of 4 hazard quartiles, because hazard_validation.csv is the per-ward
table rather than the quartile summary. 198 thin bars still look like a chart.

Run:  python tests/run_ui_smoke.py
Exit code is non-zero if any assertion fails, so it can gate a deploy.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs/index.html"
SUITE = Path(__file__).parent / "ui_smoke.js"
CHROME = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Chromium.app/Contents/MacOS/Chromium",
          "/usr/bin/google-chrome", "/usr/bin/chromium")


def chrome():
    for c in CHROME:
        if Path(c).exists():
            return c
    sys.exit("no Chrome/Chromium found - install one to run the UI smoke test")


if __name__ == "__main__":
    if not PAGE.exists():
        sys.exit(f"{PAGE} missing - run `python src/build_atlas.py` first")
    suite = SUITE.read_text()
    # surface any throw inside the harness as the page title, so a broken test is
    # distinguishable from a broken page
    suite = (suite.replace("(function(){", "(function(){try{")
             .replace("})();", "}catch(err){document.title='THREW '+err.message;}})();"))

    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "harness.html"
        harness.write_text(PAGE.read_text().replace("</body>", suite + "</body>"))
        dom = subprocess.run(
            [chrome(), "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=15000", "--dump-dom", f"file://{harness}"],
            capture_output=True, text=True).stdout

    title = re.search(r"<title>([^<]*)</title>", dom)
    if not title:
        sys.exit("no <title> in the rendered DOM - the page failed to load at all")
    t = html.unescape(title.group(1))
    if t.startswith("THREW"):
        sys.exit(f"the harness itself threw: {t}")
    m = re.match(r"UITEST (.*)", t, re.S)
    if not m:
        sys.exit(f"tests never ran; page title was {t!r} - a script error before the suite")

    r = json.loads(m.group(1))
    for line in r["all"]:
        print("   ", line)
    print(f"\n  {r['pass']}/{r['total']} interaction checks pass")
    if r["fails"]:
        print("\n  FAILURES:")
        for f in r["fails"]:
            print("   -", f)
        sys.exit(1)
