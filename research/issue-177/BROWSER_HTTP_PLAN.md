# Issue #177 follow-up — real source installed browser HTTP search

## Evidence and user gap
- On exact main `89f4f24b0e49055a649adfe323219a17883409ae`, merged PR #180 real pinned CI https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/39385352888 proved installed 0.1.0 wheel, original TT conversion, source byte digest parity, 11,300 canonical word slots from exactly two immutable TT records, 162 Horner labels, native query, and the non-serving browser `--check`.
- The older pinned real Mark browser regression `research/issue-58/web_app_smoke.py` already verified `setup_browser(False,...) /query` returns HTTP 200 through Flask test_client, on actual pinned source but via converter implementation rather than installed wheel. It did **not** POST a researcher query to live WSGI.
- The genuine gap under #177 is researcher-facing HTTP/search interaction on freshly built, clean-wheel installed TF, not another full corpus conversion or custom app.

## Research → plan → RED → implementation
1. RED-first extend `tests/test_issue177_agent_smoke.py` requiring a new independent `/query` POST roundtrip, loopback-only server, structured reply count/status and guaranteed shutdown. Before implementation this fails on missing service code, preserving existing #180 CLI/Horner smoke.
2. Extend the existing exact-pinned original Thomas+Pistis script **after** `copticscriptorium-tf-web --check`. Use the installed wheel's packaged `tf_app/config.yaml` via Python `importlib.resources`, then the public Text-Fabric 13.1.0 `setup_browser(False, app:, --locations=, --modules=.)`, and Werkzeug `make_server("127.0.0.1", 0, ...) ` to avoid exposing port to the network. Make real `urllib` GET `/` and POST `/query` with actual search template `word`. Require HTTP 200, HTML home page, JSON response `status: true`, nonempty result HTML and `nResults == api.F.otype.maxSlot` (11,300 pinned source words).
3. Close server in `finally` even on errors. No original Coptic/English witness text, request HTML, result table, traceback echo of original source or derived TF files in CI artifacts. Log only query template type, integer count and result booleans; avoid external port forwarding.
4. Exact-head CI should run focused tests, all repo tests, and pinned real installed wheel job; independent skeptical adversarial review should examine actual source/API and output. A failure may reveal an actual browser bug in subset navigation or a mistaken form assumption; research real response before changing anything.
5. Merge only on exact passing CI and reviewed SHA. **Do not mark graphical JS/DOM click automation or agent-driven registered Agora UI complete** based on plain HTTP route checks; #177 stays open for those remaining independent explorations.

## Scope
- No converter format changes; extend the already vetted bounded source smoke, not build more test orchestration.
- The pinned Text-Fabric browser route receives real user form data via loopback WSGI; current upstream implementation shape is background research, exact supported pinned wheel must be checked by CI.
