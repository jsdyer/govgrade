# Gov Grade

A static, dated evidence viewer for security-header and TLS provider assessments of selected Canadian websites. Works at `https://coolcode.ca/govgrade/`. Browser controls operate on versioned JSON; they never submit scans.

<!-- coolcode:guide -->
Inspect the saved CoolCode header report and individual MDN findings. The owner can run Personal TLS · Check CoolCode in GitHub Actions using SSLLABS_EMAIL, then open the provider report from the run Summary. Existing MDN JSON imports stay in this tab for comparison. Available reports are shown first; uncollected government targets appear only when explicitly viewing coverage notes.
<!-- /coolcode:guide -->

## Actual coverage and limitations

| Selected host | Scope | Initial collection |
| --- | --- | --- |
| coolcode.ca | Operator-owned Canadian reference | MDN Observatory enabled |
| www.canada.ca | Federal portal | Paused; no grade inferred |
| www2.gov.bc.ca | British Columbia portal | Paused; no grade inferred |
| www.ontario.ca | Ontario portal | Paused; no grade inferred |
| www.quebec.ca | Quebec portal | Paused; no grade inferred |
| www.alberta.ca | Alberta portal | Paused; no grade inferred |

MDN's official [FAQ](https://developer.mozilla.org/en-US/observatory/docs/faq) permits public domain assessments. However, automatic approval review blocked government assessment requests in this development session because they might initiate new scans and the reviewer did not consider provider permission evidenced. No retry or alternate route was used for those sites. The deployed collector deliberately rejects enabling government rows. The owned reference was successfully assessed. This is partial coverage, not a government security ranking.

The [official GET implementation](https://github.com/mdn/mdn-http-observatory/blob/main/src/api/v2/analyze/index.js) uses recent cached reports when present and performs a fresh remote assessment when absent/expired. The GET response includes tests and provider history. There is no established cache-only public history endpoint: `/api/v2/history` returned 404. `/robots.txt` on the API host returned 404. One bounded, owner-authorized `GET https://observatory-api.mdn.mozilla.net/api/v2/analyze?host=coolcode.ca` is currently made per scheduled run. No arbitrary hostname form, bulk scan, IP substitution, private target, or network bypass exists. Provider history may have unknown old algorithm versions, so automatic score comparisons require matching known versions across our captures.

## SSL Labs API v4: registration is not public-use permission

The adapter reads **SSLLABS_EMAIL** only from the collector environment / repository Actions secret. It never embeds or logs that value, and its request headers are not archived. The [v4 documentation](https://github.com/ssllabs/ssllabs-scan/blob/master/ssllabs-api-docs-v4.md) specifies the `email` request header. Registration alone does not authorize this public site to collect or publish third-party reports.

The [Qualys terms v2.2](https://www.ssllabs.com/downloads/Qualys_SSL_Labs_Terms_of_Use.pdf), API licence restrictions, require site-owner scanning permission and express Qualys permission for public-site API use; publication requires the owner's express permission. `fromCache=on` is **not cache-only** and can initiate an assessment on a miss. Public API report republication remains separate from personal use. The owner-only client below assesses the authorized CoolCode site and links to the provider report; it does not copy the API report into the public application.

To enable a reviewed target after actual permissions exist, record the provider permission reference in `config/sites.json` as `ssl_labs_publication_permission`, its site-owner authorization as `owner_permission`, its publication authorization as `publication_permission`, set `ssl_labs_enabled` true, and supply the registered secret. The collector first obtains `/info`, prints all provider messages, then makes at most one `/analyze?host=…&fromCache=on&all=done` call per authorized target. It preserves READY/ERROR/DNS/IN_PROGRESS states and all endpoint grades without inventing a global TLS grade. It does not poll or force new scans. The public app has no live API proxy. Qualified use is subject to the provider's permission terms, not this software's MIT licence.

## Run your personal TLS check now

Open [Personal TLS · Check CoolCode](https://github.com/jsdyer/govgrade/actions/workflows/personal-tls.yml), choose **Run workflow**, and open the completed run **Summary**. The registered `SSLLABS_EMAIL` secret is used only in API headers. The workflow assesses only `coolcode.ca`, prints the required provider notices before assessment, polls at 20-second intervals, and returns the official SSL Labs report link. It does not commit API reports or publish endpoint grades on the app. Only users with repository workflow permissions can invoke it. The initial installation or an edit to this workflow verifies the owned site once; there is no scheduled personal TLS scan.

For local personal noncommercial use, clone this MIT-licensed repository, set `SSLLABS_EMAIL` in your environment, then run `python3 scripts/ssl_personal.py`. The local client prints the full JSON report after completion. `--links-only` suppresses that JSON, as used in CI. SSL Labs performs the remote assessment; only owned/authorized infrastructure is in scope. Its terms and `/info` messages are printed before the request. A cached report up to 24 hours old may be reused. The public page is not an API proxy; visitors can use the SSL Labs website directly for their own sites.

## Data lifecycle

- `.github/workflows/pages.yml` refreshes at **07:43 UTC Sundays** (`43 7 * * 0`). Manual dispatch can opt into `refresh`; normal build/deploy stays offline.
- Python standard-library collector: `python3 scripts/collect.py`. Validation precedes publication. A source failure prevents refresh/deploy and leaves prior published data intact.
- `data/history/<UTC>.json` is append-only; exact raw provider responses are content-addressed in `data/raw/`. `data/manifest.json` holds SHA-256 hashes. Builds verify history and source hashes. Existing captures are never overwritten.
- `data/index.json` is the small hub summary, with capture timestamp, latest path, counts and explicit partial coverage.
- Provider assessment time, capture time, algorithm version, source URL and raw hash are retained separately. An older provider report is not represented as freshly assessed.
- After the schedule's Python/Node/browser checks pass, the workflow commits only data and deploys that build. Failed checks never replace a good Pages deployment.

## Browser behaviour and privacy

Search, coverage filters and capture selection run locally. JSON imports are at most 2 MB, validated, retained in tab memory only, and cleared when switching capture. MDN responses do not verify their hostname within the imported payload, so the selected host association is explicitly unverified. Exports flag local imports. Imported HTML-like strings are rendered as text. CSV cells escape quotes and neutralize formula prefixes. The shared CoolCode counter sees aggregate tool opens, not filters or file content. Clicking source links opens those providers directly.

## Checks and publishing

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The offline build copies validated data and browser assets to ignored `dist/`. CI additionally installs the test-only Playwright dependency and checks the real UI at a project subpath, filtering, paused states, CSV downloads, safe local imports, and desktop/mobile overflow. It uploads screenshots. Browser installation is unnecessary for the app. GitHub Pages deploys successful `main` runs. No `CNAME` belongs in this repository.

Software: MIT. Provider facts are attributed to MDN Observatory and Qualys SSL Labs; their respective service terms remain applicable. This project is independent and is not endorsed by either provider. An assessment is not a complete security audit.
