# Claude Cowork and Skills for call-recording QA (research as of 2026-11-20)

Note on method: about 12 tool calls. Official pages were fetched directly where possible (claude.com/docs, support.claude.com, platform.claude.com). news.zoom.com and claudelab.net were not reachable from the research sandbox, so those claims rest on search-result summaries only and are flagged.

## What Cowork is and how it runs code/tools (VM, folders, network, packages, limits)

### Takeaway
Cowork is Claude Desktop's agentic mode (same architecture as Claude Code, no terminal). Shell commands run in a Linux VM, with access limited to connected folders. Network access from that VM is governed by a setting in Settings > Capabilities. The default egress level is the key risk for a Whisper-in-sandbox design. The official docs do not list preinstalled packages or resource limits. The only numbers found come from a self-reported user gist.

### Cited Findings
- Cowork "uses the same agentic architecture that powers Claude Code, accessible within Claude Desktop without opening the terminal." Claude "reads and writes local files without requiring manual uploads or downloads." — [Cowork overview](https://claude.com/docs/cowork/overview.md)
- Cowork loads the connectors, skills and plugins enabled for your claude.ai account, synced at session start. It "doesn't read the Claude Code CLI's `~/.claude` directory." Skills that exist only in `~/.claude` must be added in Customize. — [Cowork overview](https://claude.com/docs/cowork/overview.md)
- "Claude can only read and write files in folders you've connected." Desktop is in beta on all paid plans. Plans listed: Pro, Max, Ultra, Team, Enterprise. — [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork.md)
- The same article says sessions run remotely on Anthropic's servers in an isolated environment, while the network-access doc says tasks run in a VM on your computer. The two descriptions are inconsistent. Search results also showed different versions of the getting-started article (an older one says "local agent mode"). — [Get started](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork.md); [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Permission modes: Manual, Auto (an automated check reviews actions) and Skip. Permanent deletion always requires explicit approval. — [Get started](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork.md)
- "When a Cowork task runs on your computer, Claude runs its shell commands in a virtual machine (VM). Your network settings decide which hosts those commands can reach." Settings are in Settings > Capabilities. On Team and Enterprise, an admin sets them in Organization settings > Capabilities. — [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Network table, quoted. "Allow network egress" off: `anthropic.com` and `claude.com` hosts only. Domain allowlist "None": those plus "Additional allowed domains". "Package managers only": the same, "plus common package registries and `github.com`". "All domains": any host, unless the org applied the HIPAA configuration. — [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Package registries and github.com are download-only. Installs work and publishing is blocked. The docs name `registry.npmjs.org`, `registry.yarnpkg.com`, `crates.io` and `github.com`. PyPI is not named in the table, although "common package registries" is stated. — [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Connectors, desktop extensions and local MCP servers are not subject to these VM network settings. Connector requests are handled outside the VM. Plugin-added MCP servers may be an exception when `requireCoworkFullVmSandbox` is on. — [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Egress settings also do not cover web fetch, web search, or MCPs including Claude in Chrome. — [Get started](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork.md)
- User-reported VM specs (self-reported by Claude inside the sandbox, so not authoritative): Ubuntu 22.04.5, Python 3.10.12, pip 22.0.2, Node 22, GCC, about 3.8 GiB RAM, no swap, 10 GB root disk plus 10 GB session disk. macOS session: 4 ARM64 cores. Windows session: 2 vCPUs. ffmpeg is not mentioned in either report. The macOS report shows a bubblewrap sandbox with `--unshare-net` and traffic through a local proxy. — [simonw gist](https://gist.github.com/simonw/35732f187edbe4fbd0bf976d013f22c8)
- A search-result summary of a third-party post (page itself not fetched, so unverified) says plain `pip install` in Cowork hits PEP 668 "externally-managed-environment", with workarounds `--break-system-packages`, a venv or uv, and that the VM's Python changes may not persist across sessions. — [claudelab.net article, via search summary](https://claudelab.net/en/articles/cowork/cowork-bash-pip-pep668-externally-managed-fix)
- A GitHub-style issue titled "Allowlist npm registry in Cowork sandbox to enable built-in slide-deck-designer skill" exists, showing that registry reachability in the sandbox has broken skills for users (content not read). — [claudeissues.com](https://claudeissues.com/issue/43334-allowlist-npm-registry-in-cowork-sandbox-to-enable-built-in-slide-deck-designer)

### Inferences
- A 10-minute call on about 4 GB RAM and 2 to 4 CPU cores is feasible for faster-whisper small/base models with int8 on CPU. I found no benchmark in any source, so treat speed as unverified. Medium and large models are riskier on 3.8 GiB RAM.
- Because ffmpeg is unconfirmed, the skill should check for it and fall back to `pip install imageio-ffmpeg` or `av` (this needs PyPI to be reachable).

### Gaps
- No official list of preinstalled packages, CPU and RAM limits, or per-task time limits for the Cowork VM was found.
- Whether PyPI (`pypi.org`, `files.pythonhosted.org`) is on the "Package managers only" list is not stated explicitly in the fetched page.

## Skill structure, upload/sharing, triggering, limits, best practices

### Takeaway
A skill is a folder with a required SKILL.md (name and description frontmatter) plus optional scripts and reference files. It is uploaded as a ZIP in Customize > Skills. Team and Enterprise owners can provision it org-wide or share it. Claude triggers it from the description only, and it requires code execution to be enabled.

### Cited Findings
- Frontmatter: `name` max 64 chars, lowercase letters, numbers and hyphens, no XML tags, no reserved words `anthropic` or `claude`. `description` non-empty, max 1,024 chars, no XML tags, should say what the skill does and when to use it, written in third person. — [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md)
- "Keep the `SKILL.md` body under 500 lines." Keep references one level deep from SKILL.md. Reference files over 100 lines should have a table of contents. — [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md)
- Progressive disclosure: at startup only name and description are pre-loaded. SKILL.md and other files are read on demand. Scripts can be run via bash without loading their contents, so only output costs tokens. — [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md)
- Layout example: `SKILL.md`, reference `.md` files, and `scripts/` (utility scripts "run, not loaded"). Prefer pre-made scripts for deterministic work, with explicit error handling, and say clearly whether Claude should run or read a script. — [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md)
- Dependencies: "claude.ai: Can install packages from npm and PyPI and pull from GitHub repositories. Claude API: Has no network access and no runtime package installation." List required packages in SKILL.md and do not assume they are installed. — [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md) (this describes claude.ai/API, not Cowork's own allowlist, which is stricter by setting)
- Other guidance: build evaluations first (at least three), test with Haiku, Sonnet and Opus, use validate-then-fix feedback loops, use template and examples patterns for output format, use forward slashes in paths, and use fully qualified MCP tool names (`ServerName:tool_name`). — [Best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md)
- Triggering: "Claude decides when to use a skill based on your request." The description signals when it applies. If it does not fire, check it is toggled on, clarify the description, or name the skill in the prompt. — [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- Upload: package the skill folder as a ZIP, then Customize > Skills > + > Create skill > Upload a skill. No numeric size limit is stated. Failure causes listed: oversized ZIP, folder name not matching skill name, missing SKILL.md, invalid characters. — [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- "Skills require the code execution environment to function." Enable "Code execution and file creation" (Free/Pro/Max/Ultra). Team has it on by default. Enterprise owners enable both it and Skills. — [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- Sharing (Team/Enterprise): requires an owner to enable toggles. Share with people, or groups (Enterprise). Shared skills are view-only, stay off until the recipient enables them, and updates reach recipients automatically. Works in chat and Cowork. Publishing to the org library can require admin review. — [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- Org provisioning: owner-provisioned skills are enabled by default for all users (users can toggle off). Enterprise can scope skills to groups by bundling them in a plugin. Upload is a .zip that "must include a SKILL.md file". Users can submit skills or plugins to an organization library. No file size limits stated. — [Provisioning and managing skills](https://support.claude.com/en/articles/13119606-provisioning-and-managing-skills-for-your-organization)
- Plugins "bundle skills, connectors, and more into shareable packages." — [Cowork overview](https://claude.com/docs/cowork/overview.md)

### Inferences
- A QA skill should be named something like `scoring-call-recordings`, with a description listing triggers such as "call recording, transcript, QA scorecard, PDF report". The scorecard rubric belongs in `references/scorecard.md`, and a `scripts/make_report.py` should produce the PDF deterministically.
- To distribute to a team, provision via org settings (Team/Enterprise) or bundle as a plugin with the transcript connector.

### Gaps
- Numeric ZIP size limit not documented in the pages read. I did not read the Agent Skills overview page or the anthropics/skills GitHub repo or the engineering blog post, so frontmatter fields beyond name and description (for example `allowed-tools`, `compatibility`) are unverified here.

## Speech-to-text inside the sandbox and network restrictions

### Takeaway
No source documents running Whisper in Cowork. Technically it needs ffmpeg, a Python package (PyPI) and a model download (usually huggingface.co), and the documented allowlist options only guarantee package registries and github.com. Hugging Face is likely blocked unless the allowlist is "All domains" or the host is added under "Additional allowed domains".

### Cited Findings
- Allowlist levels and where to change them: see network table above. Admin sets org-wide on Team/Enterprise. — [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Whisper-style skills commonly require Python plus openai-whisper and ffmpeg, download the model on first run (about 150 MB for base), and convert audio to 16 kHz mono WAV. — [skills.sh and ClawHub audit pages via search](https://clawhub.ai/josunlp/whisper-transcribe/security-audit)
- An OpenWhispr doc says local model downloads need `huggingface.co`, `cdn-lfs.huggingface.co` and `cdn-lfs-us-1.huggingface.co`. — [OpenWhispr](https://docs.openwhispr.com/help/fix/model-download-fails.md) (from search summary, not fetched)
- whisper.cpp models are fetched from huggingface.co/ggerganov/whisper.cpp in several skills (search summary). — [ClawHub local-whisper-cpp](https://clawhub.ai/wuxxin/local-whisper-cpp/security-audit)
- Cowork network blocks are reported in command output (for example `403 Package registry is download-only`). — [Network access](https://claude.com/docs/cowork/guide/network-access.md)

### Inferences
- Options in order of robustness: (1) use a connector that already supplies transcripts, which avoids the VM entirely; (2) set the allowlist to include `huggingface.co` and its CDN hosts under "Additional allowed domains", then pip install faster-whisper; (3) ship the model weights inside the skill ZIP (size limit unknown, a small/base int8 model is roughly 100-500 MB, which is probably too large); (4) transcribe outside Cowork and give Claude the transcript file.
- CPU speed for a 10-minute call is unverified.

### Gaps
- No tested report of faster-whisper or whisper.cpp running in Cowork. No confirmation of which hosts "common package registries" includes (PyPI, Hugging Face).

## Connectors that supply transcripts; PDF generation and return

### Takeaway
Zoom, Fireflies, Otter, Granola and Fathom have Claude connectors per third-party sources. Gong's own hosted MCP reportedly does not return raw transcripts. Quo is available as a tool in this environment. PDFs are best made in a skill script (reportlab or the built-in pdf skill) and saved to a connected folder.

### Cited Findings
- Zoom MCP connector gives access to meeting summaries, transcripts, recordings and scheduling, and works in Cowork (vendor and press summaries; not verified on the Zoom page). — [Zoom news](https://news.zoom.com/zoom-meeting-intelligence-in-claude/); [UC Today](https://www.uctoday.com/?p=531277)
- Fireflies connector launched August 2025. Otter's connector was published April 2026 (read-only). Granola's launched February 2026. Fathom can only expose meetings it captured live. — [Fellow roundup](https://fellow.ai/blog/ai-meeting-notetaker-claude-connector/); [tl;dv roundup](https://tldv.io/blog/best-claude-connectors/) (vendor blogs, indicative only)
- Gong: Gong's hosted MCP reportedly returns AI insights, not raw transcripts. Third-party servers (Workato, Gumloop, `gongio-mcp`) can return transcripts. Gong is not in Anthropic's directory per tl;dv, so a custom connector on a paid plan is needed. — [Workato Gong MCP](https://docs.workato.com/mcp/registry/gong-mcp-server); [tl;dv Gong MCP](https://tldv.io/blog/gong-mcp/); [Boomi](https://help.boomi.com/docs/Atomsphere/Connect/MCPConnectors/gong-proxy)
- Quo (OpenPhone): in this research session a Quo MCP server exposes `fetch-call-transcripts` and `fetch-calls` tools (observed in the session's tool list, no public URL read). Whether Quo transcripts exist for every call (plan-dependent) is unverified.
- Microsoft 365 connector tools seen in the session include SharePoint search/upload and Outlook (observed in the session's tool list); Teams transcript access was not verified. Google Drive/Sheets connectors exist (Sheets tools observed).
- Connectors run outside the VM, so the Cowork network allowlist does not restrict them. — [Network access](https://claude.com/docs/cowork/guide/network-access.md)
- Cowork produces "polished deliverables including Excel spreadsheets with functional formulas, PowerPoint presentations, and formatted documents." — [Cowork overview](https://claude.com/docs/cowork/overview.md)
- Anthropic ships a `pdf` skill (create PDFs, merge, extract, fill forms) in the skills available to Claude (from the skill list in this session). A script can use reportlab (PyPI), which needs package install access. — [Best practices PDF example](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md)

### Inferences
- Simplest robust design: connector fetches transcript (or user drops a transcript file in the connected folder), the skill scores it against a `references/scorecard.md` rubric, and `scripts/make_report.py` writes a PDF into the connected folder.
- For audio-only sources (such as Quo recordings or uploads), STT is the weak point, so plan for either an allowlist change or an external transcription service.

### Gaps
- Could not verify Zoom, Otter, Fireflies details on first-party pages. No first-party confirmation that reportlab is preinstalled in Cowork's VM.

## Known limitations and gotchas

### Takeaway
Main gotchas are inconsistent documentation about where Cowork runs, network restrictions on package installs and model downloads, PEP 668 pip errors, session sharing limits, and view-only shared skills.

### Cited Findings
- Sessions cannot be shared with others (artifacts can). Some features (certain live artifacts, plugins with local MCP servers) are desktop-only. Multi-step tasks use more usage. — [Get started](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork.md)
- Shared skills are view-only and off until the recipient enables them. Admins cannot browse contents of skills shared between members (from search summary). — [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- Upload failures: folder name must match skill name, SKILL.md is required. — [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- Admin UI labels for skills settings vary across support-article versions ("Skills", "Plugins & skills", "Policy"). Check your own console. — [Support search results](https://support.claude.com/en/articles/12512180)
- Registry blocks have broken built-in skills for some users. — [claudeissues.com](https://claudeissues.com/issue/43334-allowlist-npm-registry-in-cowork-sandbox-to-enable-built-in-slide-deck-designer)
- Connector prompt-injection and permission-escalation risks are noted by third-party writers. — [Fellow roundup](https://fellow.ai/blog/ai-meeting-notetaker-claude-connector/)

### Inferences
- Transcripts from recordings are untrusted input, so the skill should instruct Claude to treat transcript content as data.

### Gaps
- Did not find Reddit or Hacker News threads on Cowork speed or reliability, or anything on release notes from late 2026. Pricing and usage limits were not researched.
