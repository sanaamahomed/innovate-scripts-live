# Speech-to-text options for South African telephone sales calls (as of 2026-11-20)

Research limits: ~16 web tool calls; arxiv.org and elevenlabs.io were not reachable from the sandbox (network allowlist), so those pages were seen only via search snippets. Search-tool summaries are second-hand; vendor pages and third-party price aggregators conflict in places. No independent benchmark on en-ZA / Zulu / Afrikaans telephone code-switching for the commercial engines was found.

## Which engines support en-ZA, Zulu, Afrikaans, code-switching, 8 kHz telephony?

### Takeaway
Language coverage is the main differentiator: Azure, Amazon Transcribe, Google Chirp 3 and ElevenLabs list Zulu; Deepgram lists Afrikaans (added Aug 2026) and, per one page, Zulu. For AssemblyAI and Speechmatics, Zulu/Afrikaans support could not be confirmed. No vendor publishes accuracy for Zulu-English code-switched phone audio, so the only reliable way to choose is a bake-off on your own 8 kHz calls.

### Cited Findings
- Deepgram changelog (17 Aug 2026) announces Afrikaans (af, af-ZA) as a new Nova-3 language, batch and streaming; the Models & Languages page lists Zulu (zu) in the Nova-3 multilingual set, but pages are inconsistent about where Afrikaans sits and no Zulu changelog entry was found — [Deepgram changelog](https://developers.deepgram.com/changelog/2026/8/17), [Models overview](https://developers.deepgram.com/docs/models-overview)
- Azure Speech language-support table lists af-ZA, en-ZA, zu-ZA for speech-to-text, with custom speech listed separately; one cached locale version of the page shows af-ZA fast transcription as unsupported, so versions conflict — [Azure language support](https://learn.microsoft.com/azure/ai-services/speech-service/language-support)
- Amazon Transcribe lists zu-ZA, af-ZA and en-ZA with batch and streaming — [AWS supported languages](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
- Google Chirp 3 supports 85+ languages/variants; zu-ZA and xh-ZA are listed as Preview; af-ZA and en-ZA not confirmed for Chirp 3 in what I saw — [Chirp 3 docs](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)
- Speechmatics: "55+ languages"; fixed bilingual packs listed are Arabic, Malay, Mandarin, Spanish, Tamil with English only (no English-Zulu or English-Afrikaans pack); a newer "Melia 1" multilingual model handles spontaneous switching across supported languages. Zulu/Afrikaans support not confirmed in retrieved pages — [Speechmatics docs](https://docs.speechmatics.com/introduction/supported-languages), [Melia announcement](https://speechmatics.com/company/articles-and-news/introducing-melia-multilingual-speech-to-text-model)
- AssemblyAI: Universal-3.5 Pro reported at 18 languages (one pricing table says EN/ES/DE/FR only — conflict), Universal-2 at 99 languages; Universal-3.6 Pro Realtime 32 languages. Afrikaans/Zulu not named in any result — [AssemblyAI models docs](https://assemblyai.com/docs/getting-started/models), [AssemblyAI 99 languages](https://assemblyai.com/blog/99-languages)
- ElevenLabs Scribe has a Zulu page; it reports Scribe at 34.6% WER on Zulu FLEURS and Whisper Large v3 at 93.4% WER on Zulu FLEURS. This is vendor-run comparison — [ElevenLabs Zulu STT](https://elevenlabs.io/speech-to-text/zulu) (via search snippets)
- Whisper large-v3 zero-shot Zulu: a community model card reports 41.78 on FLEURS and 53.76 on Common Voice 25, but these appear to be CER not WER; fine-tuned model combined WER 48.45. Afrikaans fine-tune card: Common Voice 25 WER 4.21, combined 16.01; zero-shot 9.6 / 10.88 (metric label unclear) — [BuzzASR Zulu](https://huggingface.co/BuzzASR/zulu), [BuzzASR Afrikaans](https://huggingface.co/BuzzASR/afrikaans)
- Open fine-tunes exist: Sunbird faster-whisper for 51 African languages (card says validate WER yourself) and a large-v3-turbo Zulu fine-tune from DSFSI — [Sunbird](https://huggingface.co/Sunbird/faster-whisper-51-african-languages), [dsfsi-anv zul](https://huggingface.co/dsfsi-anv/whisper-large-v3-turbo-anv-zul)
- AfriSwitch (arXiv 2608.26434, 2026): 61.36 h in-the-wild code-switched speech, 16 African languages; five open/commercial systems zero-shot, best averaging 35.93% WER, far above monolingual figures. Whether isiZulu/Afrikaans are included and per-system results not confirmed — [AfriSwitch](https://arxiv.org/pdf/2608.26434)
- Academic South African code-switching work (English with isiZulu/isiXhosa/Setswana/Sesotho soap-opera corpus; semi-supervised English-isiZulu LM did not improve ASR; XLSR fine-tuning study) is 2018-2023 and not on telephone sales calls — [Yılmaz 2018](https://arxiv.org/pdf/1807.10949), [Biswas 2020](https://arxiv.org/pdf/2004.04054), [2023 XLSR](https://arxiv.org/pdf/2311.15077v1.pdf)
- OpenAI gpt-4o-transcribe: one source reports 2.46% WER on FLEURS (aggregate, no per-language data); no Zulu figure found. Soniox (a competitor) claims 3.24% vs its 1.25% on Afrikaans, model unspecified — [digitalapplied](https://www.digitalapplied.com/blog/openai-gpt-transcribe-stt-model-comparison-2026), [Soniox page](https://soniox.com/compare-stt/soniox-vs-openai/afrikaans)

### Inferences
- Zulu is the weak point for every engine; Whisper zero-shot is likely unusable for Zulu segments, while Azure/Google/AWS/ElevenLabs are the candidates that at least list it. English dominates sales calls, so en-ZA accuracy plus handling of embedded Zulu/Afrikaans words matters more than monolingual Zulu WER.
- Most code-switching in sales calls is intra-sentential English with Zulu/Afrikaans words; multilingual models (Deepgram Nova-3 multilingual, Melia, Scribe, Whisper) are the relevant category, not per-language models.

### Gaps
- No independent WER for en-ZA telephone speech on any commercial engine; no Artificial Analysis or Open ASR leaderboard numbers retrieved (not searched effectively); Whisper turbo/distil, WhisperX, Nova-3 Zulu WER, Speechmatics and AssemblyAI Zulu/Afrikaans support all unverified. Run own test (see tips).

## Diarization: stereo vs models

### Takeaway
If calls can be recorded dual-channel (one speaker per channel), transcribe each channel separately and merge by timestamps; this removes diarization errors. For mono, vendor diarization or pyannote works but adds error. No published stereo-vs-diarized WER comparison on telephone data was found.

### Cited Findings
- 2025 benchmark (mono 16 kHz, includes CALLHOME): PyannoteAI best at 11.2% DER, DiariZen 13.3%; main errors are missed speech then speaker confusion — [Benchmarking Diarization Models](https://arxiv.org/html/2509.26177v1)
- Vendor claim: channel-separated audio gives perfect speaker attribution; overtalk hurts accuracy either way; diarization degrades with hold music or >2 speakers — [Medallia/Voci](https://docs.medallia.com/voci/audio-capture/audio-data-and-accuracy/single-channel-mono-and-channel-separated-audio), [pyannote.ai](https://www.pyannote.ai/blog/diarization-for-mono-channel-voice-ai)
- OpenAI gpt-4o-transcribe-diarize returns timestamped per-speaker segments — [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize)
- Google Chirp 3 diarization: sources conflict (BatchRecognize only vs also Recognize) — [Chirp 3 docs](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)
- ElevenLabs Scribe v2 speaker labels up to 32 speakers (third-party listing) — [LLM Reference](https://www.llmreference.com/provider/elevenlabs/scribe-v2)

### Inferences
- Deepgram multichannel bills per channel (one source), so stereo roughly doubles cost on per-minute-per-channel pricing; check. Stereo also helps with crosstalk (overlap can be transcribed on both channels).

### Gaps
- Quantified WER gain from dual-channel on 8 kHz calls; WhisperX diarization quality on South African accents; whether Quo exports separate channels (not found).

## Pricing, privacy/POPIA, self-hosting, speed

### Takeaway
Cloud list prices cluster at about $0.15-0.35 per audio hour; add-ons (diarization, keyterms) raise it. POPIA s72 permits cross-border processing under conditions (contract, consent, etc.); Azure/AWS have South African regions but I did not verify ASR availability there.

### Cited Findings
- AssemblyAI async: Universal-3.5 Pro $0.21/h, Universal-2 $0.15/h, per-second billing — [AssemblyAI pricing](https://www.assemblyai.com/pricing.md)
- ElevenLabs Scribe v2: $0.20/h on official API page (third parties say $0.22; one FAQ "from $0.40"); keyterm prompting +$0.05/h (term limit 100 vs 1,000 conflicting) — [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)
- Deepgram Nova-3 (third-party figures, conflicting, official page not retrieved): pre-recorded ~$0.0043-0.0052/min (~$0.26-0.31/h), diarization +~$0.002/min, keyterm +~$0.0013/min — [Deepgram pricing](https://deepgram.com/pricing), [convertaudiototext](https://convertaudiototext.com/blog/deepgram-nova-3-explained)
- OpenAI: gpt-4o-transcribe $0.006/min (~$0.36/h), mini $0.003/min (~$0.18/h), diarize listed $0.006/min via a gateway (token pricing elsewhere; unconfirmed) — [Opper](https://opper.ai/openai/gpt-4o-transcribe-diarize)
- Speechmatics: from $0.12/h on one page, $0.24/h on another, Melia as low as $0.129/h; credit based — [Speechmatics pricing](https://www.speechmatics.com/pricing.md), [Melia](https://speechmatics.com/company/articles-and-news/introducing-melia-multilingual-speech-to-text-model)
- Google Chirp 3: no official rate found; reseller $0.000267/s (~$0.96/h) — [OpenRouter](https://openrouter.ai/google/chirp-3)
- POPIA s72 governs transfers outside South Africa; typical grounds: data subject consent, binding agreement providing POPIA-equivalent protection; practical route is a data transfer/operator agreement — [Michalsons](https://www.michalsons.com/focus-areas/privacy-and-data-protection/transfers-of-personal-information-outside-south-africa), [CMS](https://cms.law/en/zaf/legal-updates/Managing-cross-border-data-transfers), [ITWeb](https://itweb.africa/article/popi-makes-cross-border-information-transfer-more-onerous/G98YdqLYEA6vX2PD)
- Academic analysis (PELJ 2024) argues s72 has shortcomings in cloud contexts — [PER 2024](https://www.saflii.org/za/journals/PER/2024/48.html)

### Inferences
- Self-hosting Whisper/faster-whisper keeps audio in SA but Zulu quality is poor without fine-tuning; hybrid is plausible: self-host or SA-region for sensitive calls. Disclose recording/transcription to callers and sign operator agreements with vendors.

### Gaps
- No Information Regulator guidance specific to call recording/ASR vendors found; speed (RTF) on CPU/GPU for faster-whisper/WhisperX not retrieved; SA-region (af-south-1, South Africa North) availability for Transcribe/Azure Speech not verified; vendor data retention/training opt-out policies not checked.

## Accuracy tips (preprocessing, vocabulary boosting, LLM post-correction)

### Takeaway
Little citable evidence was retrieved; the following are mainly practice recommendations. Keyterm/custom vocabulary features exist for Deepgram and ElevenLabs at extra cost.

### Cited Findings
- Deepgram Nova-3 offers keyterm prompting (including multilingual) as a paid add-on — [Deepgram multilingual keyterm blog](https://deepgram.com/blog/deepgram-expands-nova-3-with-10-new-languages-and-multilingual-keyterm-prompting)
- ElevenLabs keyterm prompting add-on +$0.05/h — [ElevenLabs pricing](https://elevenlabs.io/pricing/api)
- Azure custom speech listed for af-ZA, en-ZA, zu-ZA — [Azure language support](https://learn.microsoft.com/azure/ai-services/speech-service/language-support)

### Inferences (not sourced; treat as unverified practice)
- Keep native 8 kHz (do not upsample-and-denoise aggressively); keep separate channels; use lossless/high-bitrate where possible. Boost terms: Netstar, Cartrack, StarTag, DebiCheck, R239. Post-correct with an LLM using a glossary and call context, but forbid inventing content; flag low-confidence spans for human QA.
- Whisper prompt can bias spelling of product names (initial_prompt).

### Gaps
- No tests of boosting on these specific terms; no evidence for LLM post-correction gains on SA English.

## Quo (OpenPhone) transcripts

### Takeaway
Quo transcripts are convenient but a black box: documented as 40+ languages, no published accuracy, no confirmation of Zulu/Afrikaans/en-ZA, and tied to Business/Scale plans. Probably fine for rough search/summaries, not for QA-grade accuracy.

### Cited Findings
- Call transcripts and summaries support 40+ languages; unsupported languages may not transcribe accurately or at all; accuracy varies with audio quality, clarity and language complexity; requires call recording on; Business and Scale plans (other Quo material says Business only) — [Quo support](https://support.quo.com/core-concepts/calling/summaries-and-transcripts)
- Quo API has "get a transcription for a call" endpoint and the Quo MCP exposes fetch-call-transcripts — [Quo API reference](https://quo.com/docs/mdx/api-reference/calls/get-a-transcription-for-a-call.md)

### Inferences
- Quo's underlying ASR vendor is undisclosed in what I found; the API means you could pull recordings/transcripts and re-transcribe externally.

### Gaps
- Whether Afrikaans/Zulu/en-ZA are among the 40+; whether recordings are stereo/downloadable; any numeric accuracy; data residency.

## Recommendation (provisional)
Run a 2-3 hour bake-off on 20-30 real calls (manually corrected reference, stereo if possible): Deepgram Nova-3 multilingual + keyterms, ElevenLabs Scribe v2 + keyterms, Azure custom speech (en-ZA with af/zu), plus gpt-4o-transcribe as baseline and Whisper large-v3 (self-hosted) for privacy. Score WER overall and on key terms/numbers (R239, DebiCheck). Then LLM post-correct with glossary. Unverified: all rankings.
