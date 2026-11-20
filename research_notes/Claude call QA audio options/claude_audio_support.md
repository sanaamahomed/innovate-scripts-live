# Does Claude accept audio input? (state as of 2026-11-20)

## 1. Does the Messages API accept audio content blocks? Which input types are supported?

### Takeaway
No. Per current official docs, the native Messages API content blocks for user input are text, image, document (PDF/plain text) and tool/search-result blocks. There is no audio block. Anthropic's OpenAI-compat layer explicitly returns HTTP 400 for `input_audio`. A speech-to-text (STT) step is required before Claude sees a call.

### Cited Findings
- Messages API reference (platform.claude.com) lists the ContentBlockParam types as: text, image, document, search_result, thinking, redacted_thinking, tool_use, tool_result, server_tool_use, web_search_tool_result, web_fetch_tool_result, code_execution_tool_result, bash_code_execution_tool_result, text_editor_code_execution_tool_result, tool_search_tool_result, container_upload. No audio type. Image sources: base64 (JPEG, PNG, GIF, WebP), url, file. Documents: PDF or plain text. (Note: I read only the first 100k chars of a ~1.3M-char page via a summarising fetch; the audio absence is from that excerpt, so moderately, not fully, verified.) — [Messages API reference](https://platform.claude.com/docs/en/api/messages)
- Features overview lists "PDF support" and "Vision (images)" as the media features; no audio/speech feature appears in the platform, Messages API or Managed Agents tables. Also lists the Files API, Code execution tool ("Lets Claude run Python and Bash code in a sandboxed container"), MCP connector. — [Features overview](https://platform.claude.com/docs/en/build-with-claude/overview)
- OpenAI SDK compat page (models listed include claude-opus-5-5, claude-sonnet-5-5, claude-fable-5-2, etc.): "Audio and file inputs are not supported. A request that includes an `input_audio` or `file` content part returns a 400 error." Table: user content `type == "input_audio"` -> "Returns a 400 error"; `audio` and `modalities` request fields "Ignored"; response `choices[].message.audio` "Always empty". — [OpenAI SDK compatibility](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk)
- Docs state the Models API returns a `capabilities` object per model (could be checked programmatically for any audio capability; I did not query it). — [Features overview](https://platform.claude.com/docs/en/build-with-claude/overview)
- Third-party sources (lower reliability) agree: Claude has no audio input. e.g. Mozonic "Can Claude Analyze Audio? No" (could not fetch: host blocked), Suprmind (text and image only). One secondary site (claudeimplementation.com) claims audio processing via the API; this contradicts official docs and is unsupported, treat as wrong. — [search result summary, Mozonic](https://mozonic.com/blog/can-claude-analyze-audio); [claudeimplementation.com](https://claudeimplementation.com/blog/claude-supported-file-types)

### Inferences
- A recorded call (mp3/wav/m4a) cannot be sent to the Messages API as audio; it must be transcribed (ideally with speaker diarization) and the transcript sent as text.
- Anything derived purely from audio (tone, sentiment from prosody, silence, talk-over, background noise) is not available to Claude unless an upstream audio-analysis tool emits it as text/metadata.

### Gaps
- I did not read the full Messages API page or the Models API `capabilities` schema; I did not find an official statement phrased as "Claude does not support audio" other than the OpenAI-compat page.
- No official "audio" page exists in what I fetched; absence is inferred from feature lists.

## 2. Claude apps (claude.ai, desktop, mobile): do voice mode / dictation process audio files?

### Takeaway
No. Voice mode and dictation are live-microphone features that convert speech to text (and TTS back); the audio is discarded. File upload accepts documents and images only; audio is not listed.

### Cited Findings
- Upload files article: documents = PDF, DOCX, CSV, TXT, HTML, ODT, RTF, EPUB, JSON, XLSX (XLSX needs code execution and file creation enabled); images = JPEG, PNG, GIF, WebP. No mention of audio or video. — [Upload files to Claude](https://support.claude.com/en/articles/8241126-upload-files-to-claude.md)
- Voice mode: "Your speech is converted to text, the recording is deleted, and the transcript is saved in your chat history." Replies are spoken in preset voices. Beta, all plans, on iOS, Android, Claude Desktop and web. "In Claude Cowork and Claude Code, dictation is available but voice mode isn't." — [Use voice mode](https://support.claude.com/en/articles/11101966-use-voice-mode)
- Dictation: converts speech to text for prompts; by default audio is deleted after conversion; opt-in sharing of recordings on Free/Pro/Max/Ultra. — [Using dictation on the Claude mobile apps](https://support.claude.com/en/articles/10065434-using-dictation-on-the-claude-mobile-apps)
- July 2026: voice mode upgraded to run on Opus and Sonnet (previously Haiku), 11 languages; reporting says the underlying voice stack is turn-based, with TTS (ElevenLabs per TestingCatalog, unverified), not a native speech model. — [9to5Mac 2026-07-23](https://9to5mac.com/2026/07/23/anthropic-upgrades-claude-voice-mode-with-more-powerful-models/); [MacRumors 2026-07-24](https://macrumors.com/2026/07/24/claude-voice-mode-opus-sonnet-model-support); [eWeek](https://www.eweek.com/news/anthropic-claude-voice-mode/)

### Inferences
- Voice mode could be used by playing a call aloud into a microphone (speaker-to-mic). That is an unsupported hack: poor quality, no diarization, not recommended.

### Gaps
- Did not verify whether desktop/web has any hidden audio-upload path; the help article does not list one.
- Voice-mode vendor details (ElevenLabs, STT provider) come from secondary reporting.

## 3. Claude Cowork specifically

### Takeaway
Cowork's documented supported file types do not include audio. No official source says Cowork can "listen to" or transcribe an audio file. Whether Claude in Cowork would run tools/code in its sandbox to transcribe an audio file is undocumented; the documented route is a transcription connector/MCP, or transcribing first.

### Cited Findings
- Cowork product page "Cowork can understand the following file types": Word, PDF, plain text, Markdown, HTML, JSON, CSV, TSV; Excel; PowerPoint; images (PNG, JPG/JPEG, GIF, SVG, WebP); YAML/XML/TOML; Jupyter; code files. No audio. Says connectors can be used to view additional files. The page does not describe the sandbox or code execution. — [Claude Cowork](https://claude.com/product/cowork)
- Cowork has dictation (mic-to-text) but not voice mode. — [Use voice mode](https://support.claude.com/en/articles/11101966-use-voice-mode)
- Third-party STT vendors market Cowork connectors/MCP servers: AssemblyAI (agent uploads audio/video or submits hosted media for transcription), Gladia, CastingWords (public URLs only), Voibe (custom connector `https://api.getvoibe.com/mcp`). Seen only via search-result summaries; the Composio page could not be fetched (host blocked). — [Composio AssemblyAI for Cowork](https://composio.dev/toolkits/assemblyai/framework/claude-cowork.md); [Composio Gladia](https://composio.dev/toolkits/gladia/framework/claude-cowork.md); [Voibe](https://www.getvoibe.com/help/transcribe-audio-in-claude)
- Feature request (2026-09-08, no maintainer reply seen): configurable audio transcription endpoint for dictation in Cowork on 3P. — [claudeissues.com #92822](https://claudeissues.com/issue/92822-feature-configurable-audio-transcription-endpoint-for-dictation-in-cowork-on-3p)
- Platform docs describe a code execution tool/sandbox for Python and Bash (API side). — [Features overview](https://platform.claude.com/docs/en/build-with-claude/overview)

### Inferences
- If a Cowork session has a code sandbox with network or installable packages, Claude might be able to run a local STT library (e.g. Whisper) on a dropped audio file. This is plausible but NOT documented or verified by me; results would depend on sandbox limits (compute, package/network access, file size). Test empirically before relying on it.
- Reliable approach in Cowork: connect a transcription connector, or drop in a transcript file (txt/docx/csv/json).

### Gaps
- No official Cowork article on audio files found; I did not test Cowork with an audio file (no access).
- Cowork sandbox/network specifics not found.

## 4. Claude Code, and Bedrock/Vertex/other routes

### Takeaway
Claude Code's /voice is live dictation via Anthropic's STT service, not file transcription, and is unavailable on API-key/Bedrock/Vertex/Foundry setups. Bedrock/Vertex: no evidence of Claude audio input.

### Cited Findings
- "Voice dictation streams your recorded audio to Anthropic's servers for transcription... Requires a claude.ai account; not available when Claude Code is configured with an Anthropic API key, Amazon Bedrock, Google Cloud's Agent Platform, or Microsoft Foundry"; needs a local microphone; not in cloud or SSH sessions; transcription uses no tokens. Records up to 2 minutes. — [Voice dictation (Claude Code)](https://code.claude.com/docs/en/voice-dictation)
- Bedrock: Claude takes text and images (and documents via Converse); the Converse schema has a generic `audio` key but nothing confirms Claude support. Search found nothing on Vertex. — [Bedrock Anthropic Claude Messages API](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html); [Bedrock supported models/features](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html)
- AWS pattern: Amazon Transcribe produces transcripts, then Claude on Bedrock analyses them. — [AWS ML blog](https://aws.amazon.com/blogs/machine-learning/unearth-insights-from-audio-transcripts-generated-by-amazon-transcribe-using-amazon-bedrock)
- In Claude Code, as with the API, Claude can run Bash, so a local STT tool (e.g. Whisper, ffmpeg) can be invoked by Claude to transcribe a file; this is a general capability, not an audio feature. Not separately sourced here.

### Inferences
- The Bedrock+Transcribe pattern is the natural enterprise route; Vertex equivalent would be Google Speech-to-Text, but I found no source.

### Gaps
- Vertex AI Claude modalities not verified; Bedrock per-model Claude audio support not confirmed (absence of evidence only).

## 5. Documented practical ways to give Claude call recordings, and official guidance

### Takeaway
Universal pattern: STT (with diarization/multichannel) -> transcript text -> Claude analysis. I found no official Anthropic cookbook entry or customer story about audio/call-centre use; the guidance is from STT vendors and AWS.

### Cited Findings
- AssemblyAI contact-centre guidance: speaker diarization, multichannel stereo recordings; guides for phone-call segmentation and call sentiment analysis using an LLM gateway. — [Contact center best practices](https://assemblyai.com/docs/contact-center-best-practices); [Phone call segmentation](https://assemblyai.com/docs/guides/phone-call-segmentation); [Call sentiment](https://assemblyai.com/docs/guides/call-sentiment-analysis)
- Claude call summarisation guide notes ASR errors (AssemblyAI, Deepgram, Whisper) limit quality on noisy audio. — [learn-prompting.fr](https://learn-prompting.fr/blog/claude-call-summarization-guide)
- OpenAI cookbook on Whisper pre/post-processing (trim, segment, fix domain terms) is a generic STT reference. — [OpenAI cookbook](https://developers.openai.com/cookbook/examples/whisper_processing_guide)
- Quo MCP server exposes `fetch-call-transcripts` in this environment's tool list (a connector route where the phone system already transcribes); not independently documented here.

### Inferences
- For QA scoring, use stereo/diarised transcripts with timestamps and send in chunks; use batch processing and prompt caching for scale (both documented in the Features overview).

### Gaps
- No Anthropic cookbook example, Anthropic customer story, or official guidance on audio/contact-centre use found (one broad search plus no GitHub cookbook search; recommend a targeted check of github.com/anthropics/anthropic-cookbook).

## 6. Roadmap

### Takeaway
No announced Anthropic roadmap for native audio input found.

### Cited Findings
- Search found no announcement of a speech-native model or audio API; latest news is the July 2026 voice-mode upgrade (Opus/Sonnet, more languages) which keeps the turn-based STT -> text model -> TTS design. — [9to5Mac](https://9to5mac.com/2026/07/23/anthropic-upgrades-claude-voice-mode-with-more-powerful-models/); [Engadget](https://engadget.com/2221938/claude-voice-mode-just-got-smarter)
- Voice dictation supports 20 languages in Claude Code. — [Voice dictation](https://code.claude.com/docs/en/voice-dictation)

### Inferences
- Plan on a transcription step for the foreseeable future; re-check the API release notes before committing architecture.

### Gaps
- Did not check Anthropic release notes page or news directly; sources are press coverage. Some search-result blogs were dated after or oddly relative to today and were treated as low reliability.
