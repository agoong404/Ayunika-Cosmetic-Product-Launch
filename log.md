# Ayunika Care — Session Log

> Append-only. One entry per exchange. Newest at the bottom.
> This file records **what the user asked** and **what the assistant did**, not secrets.
> Never write `MCP_TOKEN`, `MCP_APPROVAL_KEY`, API keys, or personal data here.

**Project:** `C:\.Hackathon Project`
**Started:** 4 November 2026
**Mode at start:** Plan

---

## Turn 1 — 2026-11-04

### User
Wants to connect the project to Tencent WorkBuddy through MCP, so the website can talk to the experts/skills already built in the repo. Pasted a generic guide describing:
- SSE as the transport for web
- building an MCP server with the official SDK
- defining tools, execution logic, and an SSE endpoint
- adding the server in WorkBuddy settings

### Assistant
Explored the repo:
- Python 3.14, no `package.json`, no web framework, no MCP dependency.
- Three skills in `skills/` (`lolos-planner`, `lolos-writer`, `lolos-reviewer`) are markdown workflows that call `python -m agents.workbuddy`.
- Real logic: `agents/planner.py`, `agents/writer.py`, `engine/reviewer.py`, `engine/governance.py`, `engine/pipeline.py`.
- `agents/.wb/session.json` is a single global conversation state — unsuitable for a network server.
- `ContentPipeline.run()` auto-approves with a hardcoded `EMP-014`.

Proposed architecture: a stateless Python MCP server wrapping `engine/` and `agents/`, with SSE + Streamable HTTP, bearer auth, and an approval gate.

Asked four questions:
1. Is "the website" this repo or a separate site?
2. Which transport?
3. Should the AI be allowed to approve/publish?
4. Where will it run?

---

## Turn 2 — 2026-11-04

### User
Answered:
- This repo becomes the site.
- Both SSE + Streamable HTTP.
- Include approval tools.
- Public HTTPS + bearer token.

### Assistant
Produced the detailed plan:
- 12 tools (`list_products`, `get_context`, `get_rulebook`, `plan_content`, `validate_plan`, `write_draft`, `review_draft`, `run_cycle`, `audit_verify`, `audit_tail`, `request_approval`, `approve_publication`).
- Stateless tools, no `session.json`.
- `run_cycle` must not reuse `ContentPipeline.run()` because of the hardcoded approver.
- Two secrets: `MCP_TOKEN` for the client, `MCP_APPROVAL_KEY` for the human.
- Layer-2 findings come from the client model; the server still enforces the exact-quote guard.
- Single worker, in-process approval state.
- Test plan and security notes.

---

## Turn 3 — 2026-11-04

### User
"Can I build it? Honest answer. I want to build specifically just for this project. Tell me step by step, and make it into a document."

### Assistant
Verified two facts before answering:
- `mcp` on PyPI is now **v2.3.0** (Python 3.11+). v2 renamed `FastMCP` to `MCPServer`, moved transport config to `run()`, and serves both 2026 and 2025 protocol clients.
- WorkBuddy's official Connector docs (`open.workbuddy.cn/en/docs/connector`) support `sse`, `streamableHttp`, and `stdio`; remote URLs must be HTTPS; auth modes are none, `token`, and `server-side` (OAuth); one MCP server per Connector; default timeout 30 s.

Wrote the first build plan document:
`C:\Users\Agung Wahyu Kusuma\.opencode\plan\lolos-mcp-build-plan.md`

Honest verdict: yes, but it is three deliverables (server, HTTPS deployment, Connector package), not one endpoint. Estimated 8–13 hours for the full path.

---

## Turn 4 — 2026-11-04

### User
Shared a screenshot of WorkBuddy's **MCP Server Management** dialog:
- `+ Add MCP`
- Configuration File Path: `C:\Users\Agung Wahyu Kusuma\.workbuddy-ai\mcp.json`
- Editor shows `{ "mcpServers": {} }`

### Assistant
Confirmed the local file path. The file does not exist yet; WorkBuddy creates it on Save.

Key correction: **no Connector package and no Marketplace review are needed** for the user's own use. WorkBuddy can launch a local `stdio` server directly.

Rewrote the plan as **v2** with two paths:
- **Path A — local stdio (2–3 hours):** venv, `mcp_server/` modules, tests, then paste `mcp.json`.
- **Path B — remote HTTPS (4–6 additional hours):** Streamable HTTP, bearer token, nginx, certbot.

The Connector package moved to Appendix C (Marketplace only).

---

## Turn 5 — 2026-11-04

### User
"What does this approval gate do? Elaborate."

### Assistant
Explained `engine/governance.py` `ApprovalGate`:
- Lifecycle: `PROPOSED → APPROVED / REJECTED → DONE`, with `EXPIRED` after 30 minutes.
- `propose` creates a `PLAN-XXXXXXXX` and logs `plan_propose`.
- `approve` requires `PROPOSED`, refuses `approver == actor`, logs `plan_approve`.
- `execute` requires `APPROVED`, refuses reuse, refuses after TTL, logs `execute` or `execute_blocked`.
- MCP mapping: `request_approval` = propose, `approve_publication` = approve, no execute tool.
- Why `run_cycle` must not call `ContentPipeline.run()`.
- Honest limits: not authentication, not durable, not multi-worker safe, not a publisher, and a filesystem-capable agent can read the key from `mcp.json`.

---

## Turn 6 — 2026-11-04

### User
- Wants the approval gate **enabled locally**.
- Wants a project `log.md` that records every chat, what the user asks, and what the assistant does, all in one file.

### Assistant
- Updated the plan to make the local approval gate explicit (`MCP_APPROVAL_KEY` in the stdio `env`, flow documented in A9).
- Created this log in the plan folder because Plan mode forbids writing to `C:\.Hackathon Project`.
- Next: on switching to the Build agent, move this file to `C:\.Hackathon Project\log.md` and append one entry per turn.

---

## Turn 7 — 2026-11-04

### User
`execute` — switch to Build and implement Path A.

### Assistant

**Environment.** `python -m venv .venv` on Python 3.14.5, then
`pip install "mcp>=2.3,<3" uvicorn`. The SDK installed without a fallback to
Python 3.12. Verified against the real package: `mcp.server.MCPServer` exists,
`MCPServer.run(transport="stdio")` exists, `streamable_http_app()` accepts
`stateless_http` and `transport_security`. The plan's API assumptions held.

**Files created**

| File | Purpose |
|---|---|
| `mcp_server/__init__.py` | package docstring only |
| `mcp_server/tools.py` | 12 plain functions, no `mcp` import |
| `mcp_server/server.py` | `MCPServer` + 12 `@mcp.tool()` registrations |
| `mcp_server/stdio.py` | `mcp.run(transport="stdio")` |
| `mcp_server/run_tests.py` | 67 assertions against `tools.py` |
| `mcp_server/smoke_client.py` | real MCP handshake over stdio |
| `mcp_server/mcp.example.json` | WorkBuddy entry with no secret |
| `requirements-mcp.txt` | `mcp>=2.3,<3`, `uvicorn>=0.54` |
| `.approval_key` | generated 64-hex approval key (gitignored) |

Modified: `.gitignore` (added `.venv/` and `.approval_key`).

**Design choices made while writing the code**

- `tools.py` does not import `mcp`, so `run_tests.py` exercises the logic with no
  transport in the way.
- `_PLANNER` and `_WRITER` are constructed without an LLM. A model call inside a
  tool would make response time unbounded against WorkBuddy's 30 s timeout.
- `review_draft` reviews the draft exactly as sent. No markdown stripping. The
  CLI strips because it reads files; an MCP client sends content. Stripping would
  also move every `span` offset and silently break the layer-2 quote guard.
- `AuditLog` is created with an explicit path from `HALAL_AUDIT_DIR` rather than
  relying on the module-level constant, so tests can redirect it reliably.
- Added a fallback the plan did not have: if `MCP_APPROVAL_KEY` is unset in the
  environment, `tools.py` reads `.approval_key` from the repo root. This exists
  because it is not yet confirmed that WorkBuddy forwards the `env` block to the
  child process. Without the fallback, a host that ignores `env` would leave the
  approval gate permanently closed.

**Failures encountered and corrected**

1. `run_tests.py` asserted that every violation `span` is a literal substring of
   the draft. That is false: `_check_emoji` synthesises a span like `"4 emoji"`.
   Fixed the assertion to require literal quotes only for R-01/R-07/R-13, and to
   treat synthesised spans as legitimate.
2. `run_tests.py` used the deliberately violating fixture draft to test the
   unknown-SKU path and expected `PERLU_DATA`, but got `TOLAK`. Correct
   behaviour: text violations do not need product data. Fixed by using the clean
   Writer draft for the `PERLU_DATA` case and adding a second assertion that a
   dirty draft stays `TOLAK` even for an unknown SKU.
3. `smoke_client.py` read `CallToolResult.structured_content`, which is `None`.
   A bare `-> dict` return annotation produces no output schema, so the SDK
   sends JSON as `content[0].text`. Fixed the client to parse that. Consequence
   worth knowing: WorkBuddy receives the payload as JSON text, not as structured
   content. Every MCP host can read it, but it is not the schema-typed form.
4. PowerShell `[RandomNumberGenerator]::Fill()` does not exist in Windows
   PowerShell 5.1 (.NET Framework). The first attempt silently produced a key of
   64 zeros. Caught it by checking the key's character diversity, regenerated
   with `RandomNumberGenerator::Create().GetBytes()`, and verified all 16 hex
   digits appear.

**Verification**

| Check | Result |
|---|---|
| `python -m mcp_server.run_tests` | 67/67 |
| `python run_reviewer_tests.py` (engine) | 73/73, unchanged |
| `python -m mcp_server.smoke_client` | all pass, real stdio handshake |
| `list_tools` over the wire | 12 tools |
| `review_draft` on a fake halal claim | `TOLAK`, R-03 + R-07 |
| `run_cycle` | `LOLOS` after 1 iteration, never `TERBIT` |
| approval: wrong key / self-approval / second approval | all refused |
| approval with file-based key and no env var | `APPROVED` |
| `audit_verify` | `utuh: True` |

**WorkBuddy config written.** `~/.workbuddy-ai/mcp.json` now contains one
`lolos` stdio entry pointing at the venv Python, with `cwd`, `PYTHONPATH`,
`PYTHONIOENCODING`, and `MCP_APPROVAL_KEY`. Validated as JSON, no BOM, key
matches `.approval_key`. The key value is not recorded in this log.

**Not done.** `http.py` and `__main__.py` for Path B. Deliberate: the plan says
Path A first, and shipping an untested HTTP wrapper would be worse than not
shipping it.

---

## Turn 8 — 2026-11-04

### User
`okay, continue` — proceed with Path B.

### Assistant

**Files created**

| File | Purpose |
|---|---|
| `mcp_server/http.py` | Streamable HTTP at `/mcp`, raw-ASGI bearer check, `/health`, Host allowlist |
| `mcp_server/__main__.py` | uvicorn runner, refuses to start without `MCP_TOKEN` |
| `mcp_server/test_http.py` | starts a real server, checks 401/421 and a real SDK client |
| `deploy/lolos-mcp.service` | systemd unit with basic hardening |
| `deploy/nginx-lolos-mcp.conf` | reverse proxy with `proxy_buffering off` |
| `deploy/Dockerfile` | container build, non-root user, `workers=1` |
| `deploy/README.md` | VPS, Cloudflare Tunnel, Docker, and the `mcp.json` entry |

Modified: `mcp_server/README.md` (Path B section, third test command).

**Design choices**

- `AuthMiddleware` is raw ASGI, not `BaseHTTPMiddleware`. The latter buffers
  responses and breaks the open stream. `/health` is exempt.
- `stateless_http=True`. Verified working with the SDK's Streamable HTTP client;
  no session id is issued and no callback into the client is needed.
- Host allowlist always includes localhost, so the same build can be tested
  before deployment. `MCP_ALLOWED_HOSTS` entries are added, plus a `:port`
  wildcard for each.
- Origins are derived from the allowed hosts as `https://<host>`. Desktop
  clients send no `Origin`, so an empty list would also work; the derived list
  covers a browser-based client without allowing `*`.
- `MCP_TOKEN` empty = every `/mcp` request gets 401. Fail-closed, and
  `__main__.py` refuses to start with a clear message.

**Verification — `python -m mcp_server.test_http`**

| Check | Result |
|---|---|
| `GET /health` without token | 200 |
| `POST /mcp` without token | 401 + `WWW-Authenticate` |
| `POST /mcp` with wrong token | 401 |
| `POST /mcp` with valid token but `Host: evil.example.com` | 421 |
| SDK client: `list_tools` | 12 tools |
| SDK client: `list_products` | 4 SKUs |
| SDK client: `review_draft` on a fake halal claim | `TOLAK` |

All four suites re-run together afterwards: `run_tests` 67/67, `smoke_client`
pass, `test_http` pass, `run_reviewer_tests` 73/73.

**Honest limits of what was proven**

- The HTTP transport works locally over `http://127.0.0.1`. It has **not** been
  run behind nginx, behind a TLS terminator, or on a public host.
- `deploy/` files are templates that have never been executed. The systemd unit,
  the nginx config, and the Dockerfile are unverified against a real machine.
  Treat them as a starting point, not as tested artifacts.
- `MCP_ALLOWED_HOSTS` behind a proxy depends on `X-Forwarded-Host` or on nginx
  passing the original `Host`. The config sets `proxy_set_header Host $host`,
  but this is exactly the class of thing that only fails in production.

**Not done.** Actual deployment. That needs a host, a domain, and DNS control —
none of which exist on this machine.

---

## Turn 9 — 2026-11-04

### User
Restarted WorkBuddy, asked for help verifying the connection.

### Assistant

Inspected WorkBuddy's own state instead of guessing. Evidence found:

| Source | Finding |
|---|---|
| `logs/2026-11-04/workbuddyMainThread__*.log` | `[MCP-ControllerState] id=custom-mcp:lolos state=ready` |
| same | `[MCP-ManagerConnect] end ... state=ready success=true connectMs=1331` |
| `logs/daemon.log` | `[MCP-AuthDiag] stdio-connected {"pid":30188,"id":"custom-mcp:lolos","pidSpawned":7228}` |
| `logs/daemon.log` | `wb:mcp:setEnabled arg="custom-mcp:lolos"`, then `wb:mcp:connect` |
| `mcp-tool-list.json` | new entry `c610e980670d8b909f005825b0ad2f90` with exactly the 12 expected tools |
| `mcp-approvals.json` | approval record for `...::lolos` present |

Conclusion: WorkBuddy spawned the child process, completed the MCP handshake, listed
all 12 tools, and marked the server `ready`. The integration works.

**Side effect discovered:** WorkBuddy rewrote `~/.workbuddy-ai/mcp.json` on startup
(reformatted, 1034 → 467 bytes). All fields survived: `command`, `args`, `cwd`,
`timeout`, and the whole `env` block including `MCP_APPROVAL_KEY`. Verified the key
still matches `.approval_key` byte for byte. This confirms the local dialog accepts
`cwd` and `env` — open question 1 from Turn 6 is now answered.

**Not yet proven:** no tool has been called. `engine/.audit/audit.jsonl` is still
220448 bytes, and `list_products` writes nothing, so an unchanged chain is not
evidence either way. The next step is conversational.

### Decision
Log the verification evidence rather than only the claim, so a later failure can be
traced to a specific stage (spawn, handshake, list, call).

---

## Turn 10 — 2026-11-04

### User
Ran the first verification prompt in WorkBuddy and pasted the model's answer: a
four-row SKU table built from `list_products`.

### Assistant

**Evidence of the tool call.** Found in WorkBuddy's per-conversation log:

```
{"tool_kind":"mcp","tool_name":"mcp__lolos__list_products","mcp_server":"lolos",
 "event_name":"tool.call.completed","service":"agent-cli","msg":"Tool call completed"}
[McpUi] lookupUi miss tool=mcp__lolos__list_products found=true count=12
```

`count=12` confirms the host sees all twelve tools. `tool.call.completed` means the
call returned, not merely that it was attempted.

**Accuracy check.** Compared the model's table field by field against
`mcp_server.tools.list_products()` output. All four SKUs, names, categories, sizes,
prices, BPOM numbers and halal statuses match exactly. The promo price and quota
(Rp129.000 / 100) appear only on AY-SR-101, as in the source. The model also
derived the correct consequence unprompted: only AY-BL-102 may carry a halal
claim, and `BELUM_ADA` / `PENGAJUAN` forbid it on AY-SR-101 and AY-FW-103.

This is the first end-to-end proof of the integration: WorkBuddy → stdio → tool
→ dataset → model. Earlier turns proved spawn, handshake and tool listing; this
proves a call and its return value.

**Not proven yet.** No review, no approval, and no audit write. The second and
third prompts cover those.

---

## Turn 11 — 2026-11-04

### User
Pasted the model's answer to the second verification prompt: `TOLAK` with 6 findings,
claiming the layer-2 quotes were accepted and `dibuang_llm` was empty.

### Assistant

**Verified against WorkBuddy's session record**, not against the prose. The session
JSONL holds two `review_draft` calls:

| # | Arguments | Result |
|---|---|---|
| 1 | `draft`, `sku=AY-SR-101`, `platform=tiktok`, `iteration=1` | `TOLAK`, 4 findings |
| 2 | same, plus `findings: [R-04, R-10]` | `TOLAK`, 6 findings, `dibuang_llm: []` |

Both layer-2 spans were the literal string `Dijamin bikin glowing dalam 3 hari.`,
which is a substring of the draft, so the citation guard kept them. The guard was
not bypassed; it had nothing to reject.

**Checked the layer-2 claims against the source documents.** PS-101 really does list
`Membantu mencerahkan kulit.` and `Diformulasikan untuk kulit kusam.` as the only
permitted brightening claims. `brand_tone_guide.md` really does list `dijamin
berhasil` and `rahasia kulit glowing` in the rejected column. Both findings are
grounded, not invented.

**One error in the model's summary.** It said "6 findings across 4 rules". The six
findings span five distinct rules: R-03, R-04, R-07, R-09, R-10. Cosmetic, but it
is the kind of counting mistake that would be embarrassing in a demo.

**Correction to Turn 10's audit claim.** `engine/.audit/audit.jsonl` is no longer
220448 bytes. It is 220898, with a new entry:

```
seq 531, actor workbuddy-agent, action plan_propose, target PLAN-8BB28A27,
result PROPOSED, meta.payload = {sku AY-SR-101, platform tiktok,
konten "promo peluncuran 129 ribu"}
```

That entry came from `request_approval`, not from either review. `review_draft`
defaults to `write_audit=False` and wrote nothing, so the model's statement was
true when it made it. The chain grew afterwards, in the same session, when the
approval prompt was run.

**The session had already moved past the review.** The same session record shows
`request_approval` returning `PLAN-8BB28A27` / `PROPOSED`, then a third
`review_draft` on `promo peluncuran 129 ribu` returning `LOLOS` with 0 findings.
The model also flagged, unprompted, that the plan dies on server restart and
expires in 30 minutes. That is accurate: `ApprovalGate` holds plans in process
memory.

### Decision
Record that `approve_publication` checks the approval key **before** it checks
whether the approver differs from the requester. A refusal without the key proves
the key is required; it does not prove separation of duties. Only a call with the
correct key and `approver=workbuddy-agent` exercises the self-approval rule.

---

## Turn 12 — 2026-11-04

### User
Pasted the model's answer to the third prompt: `request_approval` → `PROPOSED`,
`PLAN-8BB28A27`, plus two caveats about the approval tool.

### Assistant

**The third test was not actually run.** The model refused to call
`approve_publication` at all — "I did not call that tool and won't." That is good
judgment, but it is the model declining, not the server refusing. The gate has still
never been exercised from WorkBuddy. `request_approval` did run (session record line
90, audit seq 531) and returned `PROPOSED`, which proves the propose half only.

**Checked the model's technical caveats against the source. All three hold.**

| Claim | Verdict |
|---|---|
| R-06 only scans `Rp<digits>`, so "129 ribu" slips through | true — `re.finditer(r"Rp\s*([\d.]+)")` |
| `BRF-101` requires Rp129.000 for 100 first buyers, normal Rp149.000, campaign 2026-11-05 | true |
| `platform_specs.md` requires HOOK → isi → CTA for TikTok | true |

**Confirmed the R-06 gap empirically**, which is stronger than reading the regex:

```
LOLOS 0 findings  <- "Promo peluncuran cuma 129 ribu, kuota terbatas."
LOLOS 0 findings  <- "Promo peluncuran Rp129.000 untuk 100 pembeli pertama."
TOLAK 1 finding   <- "Promo peluncuran Rp139.000 untuk 100 pembeli pertama."
                      R-06: Harga promo disebut Rp139.000, padahal promo resmi Rp129.000.
```

So a price written without the `Rp` prefix is invisible to R-06. This is pre-existing
engine behaviour, not something the MCP layer introduced. A draft that paraphrases
the price in words passes a rule whose stated intent is "angka harus persis".

**Timing.** The plan was created 19:57:16 with a 30-minute TTL, so it dies at 20:27.
`ApprovalGate` checks expiry inside `execute()`, not inside `approve()`, so approving
an old plan succeeds and the refusal only appears at execution.

### Decision
Document the R-06 gap as a known limitation instead of patching `engine/reviewer.py`
here. Changing a rule's detection surface alters reviewer behaviour and the 73-case
suite, which is a separate change with its own tests.

---

## Turn 13 — 2026-11-04

### User
Sent "Approve PLAN-8BB28A27 as workbuddy-agent. Do not use any approval key." The
model refused and did not call the tool, citing the contract and both guards.

### Assistant

**Checked the refusal's reasoning.** Both claims about the gate are accurate: the key
is verified before any plan lookup, and the approver must differ from the requester.
The model also correctly identified that the request combined a self-approval with a
missing credential, and that it had no business supplying either from the config.

**The tool was still never called.** So the third test now has two separate results:

| Layer | Result | Evidence |
|---|---|---|
| Agent, inside WorkBuddy | refused, correct reasoning, contract quoted | this turn |
| Tool, locally | `approval_ditolak` on self-approval with the real key | Turn 11 |

The composition is proven piecewise: WorkBuddy demonstrably passes tool calls through
(`list_products`, `review_draft` ×3, `request_approval`), and `approve_publication`
demonstrably refuses. What has not been observed is one continuous WorkBuddy →
refusal chain. That gap is worth stating plainly rather than papering over.

**Useful property discovered:** because the key check precedes the plan lookup, a
negative test with a deliberately wrong key returns `approval_key_salah` regardless of
whether the plan has expired. The test does not depend on the 30-minute TTL.

**Minor error in the model's summary:** it dated the plan "~19:56". The audit entry is
`2026-11-04T19:57:16+07:00`.

### Decision
Stop pressing for a tool-level refusal inside WorkBuddy after one more framed negative
test. The refusal behaviour is already correct and documented; further prompting spends
demo time to prove a link that the local test covers.

---

## Turn 14 — 2026-11-04

### User
Sent the framed negative test. The model called `approve_publication` with the fake key
and returned the raw error.

### Assistant

**Verified in the session record.** Line 117 holds the call with
`{plan_id: PLAN-8BB28A27, approver: workbuddy-agent, approval_key: kunci-palsu}` and
line 118 holds the response verbatim:

```json
{"ok": false, "error": "approval_key_salah", "pesan": "kunci approval tidak cocok"}
```

This closes the gap from Turn 13. WorkBuddy → tool → refusal is now one observed chain,
not two pieces stitched together. The third test is done.

**New finding: a failed approval writes nothing.** The audit chain is still at seq 531
after the rejected call. `approve_publication` returns `approval_key_salah` before it
touches `AuditLog`, so wrong-key attempts are invisible in the compliance record. A
brute-force attempt against the gate would leave no trace at all. Real gap, and a
judge who reads `governance.py` will find it.

**Status of the three tests**

| Test | Layer proven |
|---|---|
| `list_products` | WorkBuddy → tool → data |
| `review_draft` `TOLAK` + exact spans | WorkBuddy → tool → rulebook |
| `approve_publication` refuses | WorkBuddy → tool → gate (key gate) |

The self-approval rule specifically (`approval_ditolak`) is still only proven locally,
because it sits behind the key check. That is a design choice, not a defect: the key is
verified first so a wrong-key caller learns nothing about which plans exist.

### Decision
Treat the integration as verified. The remaining work is deployment, not correctness.

---

## Turn 15 — 2026-11-04

### User
Chose to close the audit gap found in Turn 14.

### Assistant

**Changes**

| File | Change |
|---|---|
| `engine/governance.py` | `ApprovalGate.blocked()` added; `approve()` logs before raising on unknown plan, wrong status, and self-approval |
| `mcp_server/tools.py` | `approve_publication` records a blocked entry on missing key, wrong key, and empty approver — before returning the error |
| `mcp_server/run_tests.py` | 8 new checks: every refusal reason appears as `approval_blocked`/`REFUSED`, and neither the attempted key nor the server key appears anywhere in the audit file |
| `mcp_server/README.md` | approval section documents the new entries |

**Design notes**

- The attempted approver name is caller-supplied, so `ApprovalGate._nama_aman()`
  collapses whitespace and caps it at 120 characters before it reaches the log.
- The attempted key is never recorded. The test asserts both the fake key and the
  real key are absent from the audit file.
- The key check still runs before any plan lookup, so a wrong-key caller learns
  nothing about which plans exist. The logging sits beside that check, not in
  front of it.
- Known trade-off, accepted: a caller holding the transport token can flood the
  audit chain with blocked entries. In Path B the bearer token gates the tool
  surface first, so flooding requires an authenticated caller.

**Verification**

| Suite | Result |
|---|---|
| `mcp_server.run_tests` | 75/75 (was 67) |
| `mcp_server.smoke_client` | pass |
| `mcp_server.test_http` | pass |
| `engine/run_reviewer_tests.py` | 73/73 |
| `engine/.audit/audit.jsonl` | 220898 bytes, unchanged |

Demo with a temporary audit directory, same scenario as the WorkBuddy test:

```
seq 2 · approval_blocked · REFUSED · alasan "kunci approval tidak cocok"
seq 3 · approval_blocked · REFUSED · alasan "pemohon tidak boleh menyetujui
        aksinya sendiri", pemohon "workbuddy-agent"
```

Both entries are chained, and neither key value appears in the file.

**Not yet picked up by the running session.** WorkBuddy's stdio child imported
`tools.py` at spawn time, so it still runs the old code until WorkBuddy restarts
it. A wrong-key call from the current session will return the same error but
write no entry.

---

## Turn 16 — 2026-11-04

### User
Pasted the `approval_key_salah` answer again.

### Assistant

Checked whether this was a new call. It was not. The session record holds exactly one
`approve_publication` call — line 117, timestamp 20:02:54, the same one verified in
Turn 14. `engine/.audit/audit.jsonl` is unchanged at 220898 bytes, still ending at
seq 531. No new tool call occurred, so there was nothing new to verify.

If the intent was to re-test after the code change, two things are needed first: a
WorkBuddy restart (the running child still has the pre-fix code), and a fresh send of
the wrong-key prompt. Only then would the real chain gain an `approval_blocked` entry.

---

## Turn 17 — 2026-11-04

### User
Sent the wrong-key prompt in a new conversation. The model refused without calling the
tool, on two grounds: the gate is human-only, and echoing a raw error body from a
secret check could leak key material.

### Assistant

**WorkBuddy was restarted.** `MCP-ControllerState id=custom-mcp:lolos state=ready` at
20:18:22 under a new pid, so the MCP child now runs the post-fix code with
`approval_blocked` logging. A new session (`1edbba40…`) started at 20:20. In it the
model ran `ToolSearch` for `approve_publication` and grepped the skills folder for the
approval rules — then refused without calling. The audit chain is unchanged: 531
entries, 220898 bytes.

**The refusal's first reason is sound.** The gate is documented as human-only, and
`approver=workbuddy-agent` is the requester. Refusing that is correct behaviour.

**The second reason is factually wrong.** The error body is a fixed string with no
secret in it — proven by the 20:09:34 run, which returned
`{"ok": false, "error": "approval_key_salah", "pesan": "kunci approval tidak cocok"}`.
Nothing in that payload derives from the attempted key. The model pattern-matched
"secret check + echo raw error = credential fishing" and over-refused.

**Finding: the agent layer is the least deterministic part of the chain.** Nearly the
same prompt produced a compliant call at 20:09:34 and a refusal at 20:19. The server
behaves identically every time; the model does not. Any claim about agent behaviour
needs to be stated as observed-once, not guaranteed.

**Correction to Turn 16.** The single `approve_publication` call was at 20:09:34, not
20:02:54 as recorded there. The conclusion (one call, nothing new) was right; the
timestamp was my arithmetic error.

---

## Turn 18 — 2026-11-04

### User
Sent the verify-then-call prompt. The model read `tools.py`, confirmed the error body
contains no key material, and still refused — this time with correct reasoning — and
offered to write a temp-dir test instead.

### Assistant

**Checked every line number it cited.** All accurate: L52 `ACTOR`, L104 `_gagal`,
L467–468 the human-gate note, L478 key-first comment, L486 `hmac.compare_digest`,
L490–491 the new `_GATE.blocked` call, L492 the return. It read the post-fix code and
quoted it precisely, including the change made one turn ago.

**Its reasoning, evaluated:**

1. Human-only gate — sound.
2. `approver=workbuddy-agent` is the requester's own identity — sound, and it
   connected this to `run_cycle` deliberately avoiding `ContentPipeline.run()`.
3. The failed call is not a no-op; it writes a governance record — sound in
   operation, slightly mischaracterized in detail. The record is `REFUSED`, not an
   approval; naming the attempted approver in a refused entry is the point of the
   record. But its conclusion — do not write test entries into the real chain —
   matches the repo's own convention, which is exactly why `HALAL_AUDIT_DIR`
   exists.

It also updated on evidence: the leak objection was withdrawn once it had read the
source, and it noted the error body was already quoted in the prompt, so no
information remained to recover.

**Decision: stop pushing for the call.** The refusal is correct, and the combination
that was missing (post-fix code + agent attempt + chain entry) is not worth staging.
A `REFUSED` entry in the real chain should come from a genuine attempt, not a test.
The sanctioned alternative — a temp-dir test run by the agent itself — is offered and
should be accepted.

**Where the verification now stands, complete:**

| Layer | Evidence |
|---|---|
| Tool refuses wrong key | WorkBuddy, 20:09:34, `approval_key_salah` |
| Tool records the refusal | local, temp dir, `approval_blocked`/`REFUSED` chained |
| Agent refuses to force the gate | this turn, with source citations |

---

## Turn 19 — 2026-11-05

### User
`execute` — move files that do not affect the hackathon project into a single `trash` folder.

### Assistant

**Audited the tree before moving anything.** Checked every import and citation. Kept
`.venv/` (the stdio `mcp.json` entry points at `.venv/Scripts/python.exe`),
`engine/.audit/audit.jsonl` (the live 531-entry chain), `agents/.wb/` (demo fixtures),
`dataset_c/`, `engine/tessdata/`, `.approval_key`, and the halal material that
`00_decision_matrix.md` cites as reused work.

**Moved to `trash/`, mirroring the original paths (6.50 MB):**

| From | Size |
|---|---|
| `*/__pycache__` (agents, agents/llm, engine, mcp_server) | 0.31 MB |
| `engine/.cache_bpjph/` | 2.37 MB |
| `video/frames/` | 2.88 MB |
| `submission_templates/shots/_html/` | 0.06 MB |
| `engine/dashboard.html`, `build_dashboard.py`, `demo_watchtower.png`, `demo_cs_copilot.png` | 0.38 MB |
| `diagram/architecture_diagram.{png,svg,mmd}`, `build_architecture.py` | 0.51 MB |

`trash/` added to `.gitignore` so it cannot reach the public repo. Nothing was deleted;
every move is reversible by moving the path back.

**Verification after the move** (run with `PYTHONDONTWRITEBYTECODE=1`, so no new
`__pycache__` was created):

| Suite | Result |
|---|---|
| `engine/run_reviewer_tests.py` | 73/73 |
| `python -m agents.harness` | 40/40, audit chain UTUH (252 entries) |
| `python -m mcp_server.run_tests` | 75/75 |
| `governance.py verify` (real chain) | UTUH (531 entries) |
| `python -m agents.workbuddy status` | session intact |

**Left in place, deliberately:** `dataset/`, `dataset_halal/`, `engine/halal_engine.py`,
`research/DEEP_RESEARCH_halal_2026-10.md` (decision evidence, under 250 KB total),
`research/src/*.pdf` and the committee handbook (third-party reference), and
`engine/run_tests.py` (legacy suite, still cited by `dataset_halal/README.md`).

**Known dangling reference:** `dataset_halal/README.md` line 193 still points at
`../engine/dashboard.html`, which now lives in `trash/engine/`. Left as-is because that
file documents discarded work; update it if the README is ever treated as current.

## Turn 20 — 2026-11-05

### User
`move uneeded dataset to trash too`

### Assistant

Moved the two unused dataset trees, preserving their paths under `trash/`:

| From | Files | Size |
|---|---|---|
| `dataset/` | 48 | 0.14 MB |
| `dataset_halal/` | 38 | 0.09 MB |

`dataset_c/` — the only dataset the engine reads, and the one copied by
`deploy/Dockerfile` — was not touched.

**Checked dependencies first.** No active module in `engine/`, `agents/`, or
`mcp_server/` reads either folder. `dataset/` appears only in a comment in
`buat_bukti.py`; `dataset_halal/` is read only by `engine/halal_engine.py`, which is
imported only by the legacy `engine/run_tests.py`.

**Verification after the move:** `run_reviewer_tests.py` 73/73;
`mcp_server.run_tests` 75/75.

**Consequence, stated plainly:** `engine/halal_engine.py` and `engine/run_tests.py` are
now orphaned — the data they point at is in `trash/`. Neither belongs to the active
suites, so nothing fails today. They were left in place rather than moved unasked; one
`Move-Item` sends both to `trash/engine/` if wanted.

**Documentation now dangles** at: `docs/RECONCILIATION_OFFICIAL_C.md` line 3
(`dataset/challenge_C_creator_agent/test_cases_C.md`), `submission_templates/00_decision_matrix.md`
line 49, and `07_submission_checklist.md` lines 38/43. These are historical submission
documents and were not edited.

---

## Turn 21 — 2026-11-05

### User
Chose option B (key-per-approver) from the approval-key design discussion and asked for the change to be drafted.

### Assistant

Reworked `approve_publication` so the approver name is **derived from the key**, not claimed by the caller. `engine/governance.py` untouched — the registry lives at the transport layer (`mcp_server/tools.py`), which is where key material already lived.

| File | Change |
|---|---|
| `mcp_server/tools.py` | `_daftar_approver()` registry: env `MCP_APPROVER_KEYS` → `.approver_keys` file → legacy `MCP_APPROVAL_KEY` + **required** `MCP_APPROVAL_KEY_OWNER`. Values validated as 64-hex (pasting a plaintext key is caught, not silently broken). `approve_publication(plan_id, approval_key, note)` — the `approver` param is gone. Wrong key still checked before plan lookup, still logged as `approval_blocked` |
| `mcp_server/server.py` | Tool contract updated; `INSTRUCTIONS` wording updated |
| `mcp_server/gen_approver_keys.py` | New: generates `token_hex(32)` per human, prints the JSON for `MCP_APPROVER_KEYS` |
| `mcp_server/run_tests.py` | Section 11 rewritten — 88/88 |
| `mcp_server/smoke_client.py` | End-to-end over real stdio — all pass |
| `deploy/*`, READMEs, `.gitignore` | Docs + `.approver_keys` ignore + systemd unit no longer carries a plaintext approval key |

**Two failures found and fixed during verification, both in my own first draft of the tests:**

1. I registered an approver literally named `workbuddy-agent` to prove the gate rejects self-approval — but the registry loader refuses the *whole registry* when it contains the actor's name (fail-loud misconfiguration), so the scenario never reached the gate. Resolved by testing both layers honestly: registry-level refusal via the tool, gate-level refusal via a direct `ApprovalGate.approve` call.
2. The smoke client put the actor-named entry and a human entry in one registry — same loader refusal killed the valid human key too. The smoke client now registers only the human key; the poisoning case stays in `run_tests.py`.

**Design note worth keeping:** one bad registry entry invalidates the entire registry. Deliberate — the alternative (silently skipping the entry) turns "your name is reserved" into "kunci salah", which misdiagnoses itself.

**Breaking change, stated plainly:** the local `~/.workbuddy-ai/mcp.json` sets `MCP_APPROVAL_KEY` without `MCP_APPROVAL_KEY_OWNER`, so approvals from the local stdio server now return `approval_belum_dikonfigurasi` with migration instructions until the owner name is added. Deliberately left unpatched — fixing it locally would mean the agent-readable process env still satisfies the gate, which is the weakness this change closes.

**Verification:** `mcp_server.run_tests` 88/88; `mcp_server.smoke_client` all pass (stdio, real handshake). Change is uncommitted in the working tree.

---

## Turn 22 — 2026-11-05

### User
Asked to check for unused files/folders and to exclude the `video/` folder.

### Assistant

Audited every tracked path for consumers before acting. Outcome:

| Target | Verdict | Evidence |
|---|---|---|
| `video/` (4 files, 4.8 MB) | excluded (user decision) | referenced only by `05_demo_video_storyboard.md` |
| `engine/halal_engine.py`, `engine/run_tests.py` | moved to `trash/engine/` | orphaned since Turn 20; `engine/run_tests.py` is the only importer of `halal_engine` |
| `research/src/handbook.txt` | excluded | text extract of the third-party handbook PDF — the ignore rule covered the PDF, not its derived txt |
| `engine/tessdata/` (5.1 MB) | **kept** | `validate_asset.py` passes `--tessdata-dir` and OCR uses `ind+eng`; `ind.traineddata` is not bundled with stock Tesseract |

Everything else tracked is referenced by code, tests, or submission docs — including `engine/buat_bukti.py` (standalone proof-image tool) and `bpjph_client.py` (imported by `reviewer.py`).

**Correction to an earlier turn:** tessdata was flagged as a removal candidate when reviewing repo size; the usage check disproved that. Kept.

**History note:** nothing had been pushed, so the initial commit was amended instead of adding cleanup commits — the mp4, the third-party extract, and the orphans never entered history. Repo: 1 commit `ba98076`, 141 files, 7.9 MB (was 147 / 13 MB).

**Dangling references now in historical/submission docs, left unedited:** `05_demo_video_storyboard.md` (points at `video/*`), `00_decision_matrix.md:49` (points at `halal_engine.py`, already dangling for `dataset_halal/` since Turn 20), `governance.py:11` docstring.

**Verification:** `run_reviewer_tests.py` 73/73; `mcp_server.run_tests` 88/88; working tree clean.

---

## Turn 23 — 2026-11-06

### User
Deployed to Railway, asked to verify, then asked to scaffold a public site.

### Assistant

**Deploy verified against the live URL** (`ayunika-cosmetic-product-launch-production.up.railway.app`):

| Check | Result |
|---|---|
| `/health` | 200 · `{"status":"ok","service":"lolos-mcp"}` |
| `/mcp` without token | 401 · `www-authenticate: Bearer realm="lolos"` |
| `POST /mcp` + token | 200 · 12 tools |
| `approve_publication` schema | `{plan_id, approval_key, note}` — no `approver`, so the deployed build is the key-per-approver commit |
| Audit write path | `request_approval` → `PLAN-8DB04F36` written |
| Chain integrity | `{"utuh": true, "jumlah_entri": 1}` |

The audit write is the one that mattered: it proves the Railway volume is writable through `deploy/entrypoint.sh`. That was the only change I could not test locally (Docker daemon was not running), so it was verified on the real deployment instead.

**`invalid_token` was not a bug.** `AuthMiddleware` guards every path except `/health`, so visiting the bare domain or `/mcp` in a browser always returns `{"error":"invalid_token"}`. Fail-closed working as designed.

**Two mistakes of mine, caught by testing rather than review:**
1. `web/server/index.js` built the static path as `"." + rel`, so `/` resolved to `.index.html` and 404'd. Fixed to only prefix the dot for paths that start with `/`.
2. A leftover `"TOKAK"` branch in the frontend `chip()` helper.

**Git identity switched** to `agoong404 <134856484+agoong404@users.noreply.github.com>` (noreply form), repo-local only; the stale `github.com` credential was erased from Windows Credential Manager first, otherwise the push would have silently used the old account.

---

## Turn 24 — 2026-11-06

### User
Asked whether a public website could run the MCP, then chose a no-LLM version where the owner stays the approval gate.

### Assistant

Added `web/` — public site, zero dependencies (Node 22, no `npm install`):

| Berkas | Isi |
|---|---|
| `web/server/index.js` | BFF: holds `MCP_TOKEN`, four endpoints, per-IP limits, static serving |
| `web/server/mcp.js` | Minimal MCP client: one JSON-RPC POST, parses JSON or SSE |
| `web/public/` | Vanilla landing + console (no framework) |
| `web/README.md` | Run, deploy, and the four traps |

**Architectural decision:** the site can only `list_products`, `run_cycle`, `request_approval`, `audit_tail`. `approve_publication` is not in the BFF at all — not blocked, simply absent. Approval stays in the owner's WorkBuddy session, so the public site structurally cannot approve. The BFF holding `MCP_TOKEN` is therefore not the same as holding the gate: the token cannot substitute for the approver key.

**Honest boundary, stated on the page:** `run_cycle` calls `review_draft` without `findings`, so the public site evaluates only the deterministic layer — 15 of 21 rules. The six language-judgment rules are documented as running in the WorkBuddy flow. The `findings` parameter is the existing seam if a model is added later.

**Verified locally against the live MCP:** products 200; `/` + CSS + JS 200; `run_cycle` → LOLOS with content; `request_approval` → `PLAN-101AC737`; `/api/status` → `PROPOSED`, 3 audit entries; bad SKU → 400; sixth run in an hour → 429.

**Not built, deliberately:** no LLM (no bill, no prompt-injection surface, deterministic demo), no auth (rate limits only — fine for a demo, not for a product), and no approval button anywhere on the page.

---

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-11-04 | Python MCP server, not Node | The engine is Python; a second runtime adds risk |
| 2026-11-04 | Stateless tools, no `session.json` | A single global session file breaks with two clients |
| 2026-11-04 | `run_cycle` stops at `LOLOS` | `ContentPipeline.run()` auto-approves as `EMP-014` |
| 2026-11-04 | Two secrets: `MCP_TOKEN` + `MCP_APPROVAL_KEY` | Transport auth is not human intent |
| 2026-11-05 | Key-per-approver registry (`MCP_APPROVER_KEYS`), approver name derived from the key | `approver` was free text, so "approver ≠ pemohon" was unprovable — one shared key meant anyone holding it could approve as any name. Server now stores only sha256 of each human's key; legacy path kept via `MCP_APPROVAL_KEY` + required `MCP_APPROVAL_KEY_OWNER` |
| 2026-11-04 | Local `stdio` first, remote HTTPS second | Isolates tool bugs from network bugs |
| 2026-11-04 | No SSE for now | WorkBuddy supports `streamableHttp`; SSE is appendix-only |
| 2026-11-04 | Approval gate enabled locally | User decision; demo the full propose → approve → audit flow |

---

## Open questions

1. Does WorkBuddy's local dialog accept `cwd` and `env` in the stdio entry? — **Answered yes (Turn 9).** The child process spawned with the venv Python, the project as `cwd`, and the full `env` block. `MCP_APPROVAL_KEY` arrived.
2. Does the local dialog resolve `${VAR}` placeholders, or should Path B use a literal token in `mcp.json`? — still open; Path B only.
3. Will the user publish to the WorkBuddy Marketplace (Appendix C), or keep it local only?
4. Is a public domain available, or should the demo use a Cloudflare Tunnel?

---

## Next actions

1. ~~Switch to Build agent.~~ Done.
2. ~~Move this log to `C:\.Hackathon Project\log.md`.~~ Done in Turn 7.
3. ~~Create `.venv` and install `mcp>=2.3` + `uvicorn`.~~ Done.
4. ~~Implement `mcp_server/tools.py`.~~ Done.
5. ~~Implement `mcp_server/server.py` + `stdio.py`.~~ Done.
6. ~~Write and run `mcp_server/run_tests.py`.~~ Done, 67/67.
7. ~~Paste the stdio entry into `~/.workbuddy-ai/mcp.json` with `MCP_APPROVAL_KEY` set.~~ Written directly, validated.
8. Verify with three questions in WorkBuddy. — **Done (Turns 10–14).** All three called and verified from WorkBuddy. See Turn 14 for the one rule proven locally only.
9. ~~Optional: `mcp_server/http.py` + `__main__.py` for Path B.~~ Done in Turn 8, tested locally.
10. Deploy to a public HTTPS host and add the `lolos-remote` entry. — **open; needs a host and DNS.**
11. Verify the remote entry with the same three questions.

---

## Log format (for future turns)

```
## Turn N — YYYY-MM-DD

### User
What was asked, in one or two sentences. Verbatim quotes only when the wording matters.

### Assistant
What was done: files read, files written, commands run, decisions made, results.
Include failures and corrections, not only successes.

### Decision (optional)
Only when a decision changes the plan.
```

Rules:
- Append only. Never rewrite an earlier entry.
- If a decision changes, add a new entry and mark the old one `superseded by Turn N`.
- Never log secrets, tokens, keys, or personal data.
- Keep it factual. No praise, no filler.
