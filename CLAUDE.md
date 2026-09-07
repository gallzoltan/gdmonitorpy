# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gdmonitor` monitors the Hungarian Government Gazette (Magyar Közlöny) for government
resolutions (*kormányhatározat*) relevant to local governments (*önkormányzat*), and mails
a digest. Code comments, docstrings and log messages are Hungarian — keep new code in that
style. It runs in production as a Podman batch container on a systemd timer (AlmaLinux 9).

## Commands

Dependencies are managed with `uv` (Python >= 3.12).

```bash
uv sync
uv run gdmonitor                     # fetch only
uv run gdmonitor --analyze --email   # the full production run
uv run gdmonitor --since 2025-07-30  # override SINCE_DATE for this run
uv run pytest
uv run pytest tests/test_sentence_splitter.py::test_does_not_split_on_house_number
uv build
podman build -t gdmonitor:latest .   # uses Containerfile
podman-compose run --rm gdmonitor    # same run via compose.yaml
```

Exit codes matter: `0` success, `1` unexpected error, `2` configuration error. systemd
relies on them, so never swallow a failure into a 0.

## Configuration

Environment variables only (`.env.example`; `find_dotenv` picks up a root `.env` in dev).
`FEED_URL`, `DB_PATH` and `DOWNLOAD_PATH` are required; `--email` additionally needs
`MSG_SERVER`, `MSG_PORT` and `EMAIL_TO`. `require_env()` in `cli.py` reports all missing
variables at once.

`SINCE_DATE` is a **static floor, never state** — nothing writes it back. Incremental
behaviour comes from the UNIQUE `gazettes.url` column and `is_already_downloaded()`.
An earlier version rewrote `SINCE_DATE` into `.env` after each run, which silently dropped
gazettes published later the same day; don't reintroduce that.

## Architecture

One batch pipeline per run, driven by `src/gdmodule/cli.py`. Four subpackages under
`src/gdmodule/`, each re-exporting its public names from `__init__.py`:

1. **`fetcher/fetch_gazette.py` — `GazetteFetcher`**: pulls the RSS feed, keeps items whose
   title contains "Magyar Közlöny", drops items published before `SINCE_DATE`, rewrites
   `megtekintes` → `letoltes` in the link to get the PDF URL, downloads into
   `DOWNLOAD_PATH`, and records the row. Deduplication is by feed URL, not filename.
2. **`gdmonitor/`** — the analysis stage: `extract_text_from_pdf` (pdfplumber, whitespace
   collapsed) → `extract_resolutions` (one regex splits the document into resolutions) →
   `analyze_gdecision` (keyword scoring, title hits count double; only above zero does it
   build a summary via `split_sentences`).
3. **`repository/repo_gazette.py` — `GazetteRepository`**: the only SQLite code. Creates
   the schema on construction, one connection per method.
4. **`sender/email_sender.py` — `EmailSender`**: POSTs an HTML digest to
   `http://{MSG_SERVER}:{MSG_PORT}/api/v1/msg` — an external relay, not SMTP. Only on
   HTTP 200 does it mark those gazette ids as sent.

State lives in three flags on `gazettes`: `analyzed` (set once processed), `relevant`
(set when a scored resolution was found; `mark_as_analyzed(..., is_relevant=False)`
deliberately will not clear an already-set flag), and `sent_email`. `--analyze` selects
`analyzed = 0`; `--email` selects `relevant = 1 AND sent_email = 0`. A fetch always runs —
the flags only add stages.

## Things that will bite you

- **Sentence splitting is deliberately hand-rolled.** `gdmonitor/sentence_splitter.py`
  replaced huSpaCy, whose only job was taking the first three sentences for the summary and
  which cost 438 MB. Gazette text is full of periods that are not sentence ends: ordinals
  (`„14.`), dates (`2024. évi`), house numbers (`Munkás u. 28.`), legal references
  (`1386/2024. (XII. 9.) Korm. határozat`) and the signature (`Orbán Viktor s. k.,`). The
  splitter guards against these with a digit check and an abbreviation list; `tests/
  test_sentence_splitter.py` pins each case. Don't swap in a naive `[.!?]` split.
- **Never pass the server's leaf certificate as a CA bundle.** `certificates/magyarkozlony-hu.pem`
  is the leaf and fails verification ("unable to get local issuer certificate");
  `_magyarkozlony-hu.pem` is the Microsec root CA and works. The code now defaults to
  `certifi`, which verifies magyarkozlony.hu fine — `CERTIFICATE_PATH` is only for a
  TLS-intercepting proxy. The old code hid this by passing `verify=False` everywhere.
- `pdfplumber` returns `None` for pages with no text layer. `extract_text_from_pdf` guards
  each page with `or ""` — without it the `TypeError` gets swallowed by the broad `except`
  and the whole gazette is silently marked irrelevant.
- The console script is `gdmodule.cli:main`. Keep the entry point inside the package —
  `[tool.hatch.build.targets.wheel] packages = ["src/gdmodule"]` means anything outside
  `src/gdmodule` is missing from the wheel, which is what broke the old `main:main`.
- Deployment has two interchangeable container definitions: the Quadlet
  (`deploy/gdmonitor.container`) and the root `compose.yaml` (+
  `deploy/gdmonitor.compose.service`). Both install as `gdmonitor.service`, so only
  one may be present; the timer is shared. Keep them in sync — volume, `:Z`,
  `keep-id` userns, host network, journald. With compose always use `run --rm`,
  never `up`: `up` swallows the exit code the systemd unit depends on.
- `database/gazettes.db` is committed and holds real run history; `downloads/` and
  `samples/` are gitignored but present locally and useful for manual checks.
