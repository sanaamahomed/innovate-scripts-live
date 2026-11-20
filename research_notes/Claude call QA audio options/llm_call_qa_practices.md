# Best practices for LLM-based call QA scoring (late 2026)

Method note: WebSearch worked but WebFetch failed (arxiv.org and kaizo.com not resolvable in this session's network allowlist), so every finding below comes from search-result summaries, NOT full-text reads. Preprint figures are unverified. Per-vendor detail for Level AI, CallMiner, Gong, Balto, Cresta, Convin and Scorebuddy was not retrieved (see Gaps). Legal points are not legal advice.

## 1. How leading products structure automated scorecards, evidence and calibration; reported accuracy

### Takeaway
Vendors describe the same pattern: a human-defined QA form scored automatically with evidence attached, plus a calibration step comparing AI to human scores. Published accuracy claims are vendor marketing; no independent benchmark was found.

### Cited Findings
- Observe.AI Auto QA evaluates voice/chat interactions against QA forms the customer defines; calibration lets QA compare the AI answer with the human score and adjust; offers auto-suggest/auto-fill/auto-submit — [Observe.AI blog](https://observe.ai/blog/a-new-era-of-qa-automation-is-here), [Observe.AI Auto QA](https://www.observe.ai/platform/auto-qa)
- Observe.AI markets "evidence QA teams can rely on" and a 23% AHT reduction across 350+ enterprises (measurement method not stated; vendor claim) — [Observe.AI Auto QA](https://www.observe.ai/platform/auto-qa)
- Trade press reports Observe.AI claiming 100% accuracy (vendor claim, not a measured result) — [CX Today](https://cxtoday.com/observe-ai-launches-a-quality-assurance-automation-solution)
- Kaizo (a competing vendor, treat framing with caution) argues "accuracy" must mean agreement with a calibrated human standard measured on your own calls, and that vague criteria score poorly; it publishes a one-week validation protocol — [Kaizo accuracy](https://kaizo.com/blog/how-accurate-is-ai-qa/), [Kaizo validation protocol](https://kaizo.com/blog/how-to-validate-ai-qa-scoring/)
- Aircall guide: calibration reveals ambiguous scorecard questions; questions where AI and analysts diverge most need refinement before rollout — [Aircall](https://aircall.io/en-gb/blog/ai-quality-assurance-call-centre/)
- Kore.ai documents "calibration sessions" as a product feature in its Quality AI — [Kore.ai docs](https://docs.kore.ai/ai-for-service/quality-ai/analyze/calibration-sessions.md); evaluAgent also markets AutoQM — [evaluAgent](https://www.evaluagent.com/auto-quality-assurance/)

### Inferences
- Common industry design: question-level (not whole-call) scoring, evidence attached per answer, and AI-vs-human calibration before auto-submit. Worth copying.
- Treat any vendor "95%+ accuracy" style number as unverified; measure on own calls.

### Gaps
- No retrieved material for Level AI, CallMiner, Gong, Balto, Cresta, Convin, Scorebuddy scorecard structure or accuracy numbers. No independent third-party benchmark of any vendor.

## 2. LLM-as-judge reliability for rubric scoring

### Takeaway
Strong judges reach roughly human-human agreement on preference tasks, but rubric scoring shows scale, order and prompt-design biases, run-to-run inconsistency and weak validity, so repeated runs, per-criterion scoring, human-labelled calibration sets and quote-grounding are needed.

### Cited Findings
- Zheng et al. (MT-Bench/Chatbot Arena): GPT-4 judge >80% agreement with human preferences, similar to human-human agreement; documents position, verbosity and self-enhancement bias and limited reasoning — [arXiv 2306.05685](https://arxiv.org/abs/2306.05685). Secondary summary: answer length correlates with win-rate; position effect weaker for GPT-4 — [InspectorRAGet](https://arxiv.org/pdf/2404.17347). Note: this is pairwise preference, not checklist QA, and did not test repeated sampling.
- Survey (Gu et al.): reliability (consistency, bias mitigation, domain adaptation) is a central open challenge — [arXiv 2411.15594](https://arxiv.org/pdf/2411.15594)
- Scoring-prompt biases named in a 2025 preprint: rubric order bias, score ID bias, reference-answer score bias, found even in advanced LLMs — [arXiv 2506.22316](https://arxiv.org/pdf/2506.22316v4)
- 2026 study using ICC: a 0-5 scale maximized human-LLM absolute agreement; 0-10 was weakest — [arXiv 2601.03444](https://arxiv.org/pdf/2601.03444)
- LLM-generated rubrics give consistency within a model but limited cross-model agreement and weaker human alignment (so use human-authored scorecards) — [arXiv 2602.08672](https://arxiv.org/html/2602.08672v1)
- 2026 preprint "Reliability without Validity": judges can be consistent yet not valid; failure modes include inconsistency across prompts/runs, systematic bias, weak domain calibration (not verified at full text) — [arXiv 2606.19544](https://arxiv.org/pdf/2606.19544)
- Judge benchmarks can be undermined by design flaws; single-shot consistency heuristics miss systemic failures — [arXiv 2509.20293](https://arxiv.org/html/2509.20293v1)
- Per-criterion judging is recommended to avoid halo effects (Autorubric framework, supports majority/weighted/unanimous ensembles) — [arXiv 2603.00077](https://arxiv.org/html/2603.00077). Conflicting: an AACL 2026 paper reports a single multi-criterion prompt was more reliable than decomposed rubric voting, and notes that averaging can beat majority vote and CoT can hurt some judges — [ACL Anthology](https://aclanthology.org/2026.aacl-long.207.pdf)
- Anthropic docs: asking for word-for-word quotes before answering reduces hallucination in long documents (>~20K tokens); have the model find a supporting quote for each claim and retract if none; allow "I don't know"; methods reduce but do not eliminate hallucination — [Anthropic docs](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)
- Voice-agent judge benchmark (2026) recommends human oversight and not treating a single judge score as ground truth without a second scoring pass — [arXiv 2608.24314](https://arxiv.org/pdf/2608.24314)

### Inferences
- Score each criterion with a small discrete scale (e.g. pass/fail/NA with evidence); avoid 0-10 holistic scores.
- Because quote requirements do not guarantee truth, verify quotes by programmatic string/fuzzy match against the transcript; reject or flag non-matching quotes.
- Run twice or more on critical items and flag disagreement for humans; measure on a human-labelled set using chance-corrected agreement (Cohen's kappa / Krippendorff's alpha), not raw %.
- Randomise/avoid relying on rubric order; keep the scorecard text fixed and versioned.

### Gaps
- No evidence found on temperature effects on judge variance, nor a controlled study on CoT vs no-CoT for call QA. No study found specifically on quote-hallucination rates in call scoring. Magnitudes of leniency bias in call QA not found.

## 3. Speech-to-text errors and verification of critical items

### Takeaway
ASR errors cluster on alphanumeric content (numbers, names, IDs) and often go unrecovered, so any compliance-critical or numeric item should be flagged for human audio verification rather than trusted from a transcript-only LLM verdict.

### Cited Findings
- Voice-agent judge benchmark: ASR errors concentrated on names, order IDs, phone numbers, emails, URLs; annotators disagreed on effect size — [arXiv 2608.24314](https://arxiv.org/pdf/2608.24314)
- "Auto Review" (ACL Industry 2025): noisy ASR output corrupts extracted fields, especially jargon and alphanumerics; proposes a second-stage LLM error check — [arXiv 2506.05400](https://arxiv.org/html/2506.05400v1)
- ASR can hallucinate content absent from audio; WER/CER often fail to reveal it — [ACL Findings 2025](https://preview.aclanthology.org/display_plenaries/2025.findings-acl.1190.pdf), [arXiv 2505.24347](https://arxiv.org/pdf/2505.24347)
- FECT: most contact-centre conversations lack explicit evidence to verify LLM-generated interpretive claims — [arXiv 2508.00889](https://arxiv.org/html/2508.00889v1)
- AssemblyAI (vendor) suggests requiring transcript quotes per score for auditability — [AssemblyAI](https://www.assemblyai.com/blog/scoring-voice-agent-calls-llm-gateway)

### Inferences
- Policy: LLM may score and cite, but must mark "needs human audio check" for: quoted prices/premiums/fees, dates, amounts, ID/policy numbers, recording/consent statements, disclosures read verbally, customer verbal agreement ("yes"), any quote with low ASR confidence or overlapping speech. Provide the audio timestamp so the reviewer listens only to that clip.
- Where the model is given audio directly (multimodal), it is still an unverified judge; apply the same flagging. (No evidence retrieved comparing audio-native vs transcript-only scoring.)

### Gaps
- No quantitative WER thresholds or SA-accent (e.g. SA English, Afrikaans/Zulu code-switching) ASR accuracy data found.

## 4. South African regulatory context, calibration, sampling, disputes

### Takeaway
Conduct rules (FAIS General Code, TCF) require accurate, non-misleading information, and POPIA governs recording and automated profiling of staff; keeping a human final decision on consequential outcomes is the safer posture. Specific recording/consent rules and sampling rates were not verified.

### Cited Findings
- General Code s3: services rendered honestly, fairly, with due skill, care and diligence; information must be factually correct and not misleading (s3(1)(a)) — [FAnews](https://www.fanews.co.za/article/compliance-regulatory/2/general/1082/ethics-and-compliance-from-principles-to-practice/42402) (secondary)
- TCF outcomes are not statutory but FSCA increasingly expects FSPs to demonstrate them; complaint-handling barriers are a TCF concern — [FAnews](https://www.fanews.co.za/article/compliance-regulatory/2/financial-sector-conduct-authority-fsca-was-fsb/1059/sloppy-complaints-handling-could-trigger-the-next-conduct-standard-avalanche/41577)
- FAIS Ombud/insurer case: a rep who went off-script during a sales call was debarred, indicating scripts/disclosures matter — [Moonstone](https://www.moonstone.co.za/life-insurer-debars-rep-who-went-off-script-during-sales-call/)
- Records of advice kept at least 5 years per commentary (not confirmed to cover call recordings) — [1Life](https://www.1life.co.za/blog/crm-compliant), [ITWeb](https://www.itweb.co.za/article/putting-ai-on-the-record/KjlyrvwBny5qk6am)
- POPIA s11: six lawful grounds, no hierarchy; consent not default; legitimate interest requires purpose/necessity/balancing and carries a right to object — [Werksmans](https://werksmans.com/wp-content/uploads/2026/01/Privacy-Day-2026-Moving-beyond-the-consent-myth-under-POPIA.pdf)
- Information Regulator direct-marketing guidance note treats phone calls as electronic communications and says outbound marketing calls must be recorded; advisory — [DLA Piper](https://www.dlapiper.com/insights/publications/2025/01/data-protection-guidance-note-on-direct-marketing)
- POPIA s71 (automated decisions): AI scoring likely not engaged where a manager reviews and finalises; automated final warnings likely would engage it; employees should be able to make representations and get info about logic; transparency, minimality and lawfulness still apply; no SA AI-specific statute — [Bowmans](https://bowmanslaw.com/insights/south-africa-ai-in-the-workplace-2-of-6-popia-considerations/), [Pinsent Masons](https://www.pinsentmasons.com/out-law/analysis/south-african-privacy-law-global-regulation-employers-ai-gov)
- Calibration: compare AI with human on the same calls and refine divergent questions — [Aircall](https://aircall.io/en-gb/blog/ai-quality-assurance-call-centre/)

### Inferences
- Design: human sign-off before any score affects an agent's pay/discipline; let agents see evidence and dispute; log model version, prompt version and transcript for audit; minimise PII sent to the model and check cross-border processing under POPIA s72 (not researched here).
- Critical-item fails (misleading info, missing disclosure, missing consent) should always route to a human regardless of LLM confidence.

### Gaps
- Not verified: whether FAIS General Code or FSCA requires recording of telephonic advice; POPIA/RICA position on recording for QA (RICA s5 party-consent is from general knowledge only, unverified); FSCA conduct standards on call recording; POPIA s72 cross-border rules for sending audio to a foreign LLM API; any ICMI/CCMA sampling rate or calibration frequency guidance (none retrieved); dispute-process standards. Recommend legal review.

## 5. Practical recommendations for a Claude-based QA workflow

### Takeaway
Synthesised design (inference from the above, not a retrieved standard): per-criterion structured scoring, mandatory verbatim evidence with programmatic verification, explicit "cannot determine" outputs, repeat runs on critical items, and human review queues.

### Cited Findings
- Quote-first grounding, permission to say "don't know", and retract-if-no-quote are Anthropic-documented anti-hallucination techniques — [Anthropic docs](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)
- Small scales and per-criterion judging are better supported than 0-10 holistic (see section 2) — [arXiv 2601.03444](https://arxiv.org/pdf/2601.03444), [arXiv 2603.00077](https://arxiv.org/html/2603.00077)

### Inferences
- Prompt structure: (1) role and purpose; (2) the scorecard as data with item IDs, weights, definitions, pass/fail examples and what counts as N/A; (3) transcript with speaker labels and timestamps; (4) instructions: quote exact text and timestamp for each item, never paraphrase as quote, output "not_evidenced" when absent, do not infer unspoken content; (5) JSON schema output per item: id, verdict (pass/fail/partial/na/cannot_determine), quote, timestamp, short reasoning, confidence, needs_human_review + reason.
- Do weighted totals in code, not in the model; fail-automatic for critical items.
- Flag for review when: critical item, number/price/ID involved, quote fails string match, low confidence, two runs disagree, audio quality poor, ambiguous/overlapping speech, or borderline score.
- Coaching view: lead with evidence-linked strengths and 1-3 improvement points per call, with clip timestamps; show trends across calls, not single scores; separate compliance (pass/fail) from soft-skill coaching; label AI output as draft pending human review.
- Validation before go-live: human-score 50-100+ calls double-blind, compute kappa/alpha per item, rewrite items with poor agreement, re-check when scorecard, prompt or model version changes; keep a rolling human sample (rate unspecified by sources; choose by risk).

### Gaps
- No published Claude-specific call-QA accuracy study found. Sampling rate figures were not found in any source.
