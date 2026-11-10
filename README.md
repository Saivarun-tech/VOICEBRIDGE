# VoiceBridge

Latest status: [completed local release work and remaining user checks](LOCAL_RELEASE_STATUS.md).

Latest full test run: [60 automated tests and 17 isolated browser suites passed](TEST_REPORT_20261102.md). Real microphone/language review is still pending.

A multilingual workspace for turning conversations into reviewed next steps.

## Verified progress — November 2, 2026

This is a local development app, not a submitted or hosted product. Core implementation is complete for the agreed scope; the remaining release checklist is below.

Implemented: editable transcript capture, persistent SQLite source library, evidence-linked reviewed tasks, task completion/reopening, Markdown handover export, literal source search, optional Gnani WAV transcription adapter, optional configured reasoning adapter with verbatim task-evidence validation. UI uses text rendering for source/model content. No credentials are bundled or saved by the app.

Added voice features: browser microphone capture capped at 29 seconds, local preview, explicit upload to Gnani, and Timbre readback of passages up to 800 characters. Returned PCM WAV headers are normalized for playback. Recording alone makes no provider request. Readback speaks the input text; it does not translate it.

Source correction/deletion is now implemented. Corrections increment the source revision, require all linked tasks to be reviewed again and block older proposals from acceptance. Deletion removes the source and linked tasks from the local workspace; previously downloaded exports are unchanged. Existing databases migrate in place. No revision history or undo is retained.

Also implemented: task editing/removal and filters; three excerpt-based report templates; selected-source AI Q&A with citation checks and abstention; local pending/completed task answers; reviewed English/Telugu/Hindi summaries and translations; JSON backup/copy restore; isolated demo mode; test observation tracking and submission preparation checklist. Full translation accepts notes up to 4,000 characters. Report templates themselves are not translated. Semantic search across the entire library and public hosting/authentication are not implemented.

Validation: 60 automated tests and 14 isolated browser suites pass after local release work. Five live Gemini checks passed with gemini-3.1-flash-lite, and both Gnani synthetic speech checks passed. See LIVE_REASONING_RESULT.md and LIVE_SPEECH_RESULT.md. Real microphone/noise quality, Telugu-English recognition and translation meaning still require human review. Matching source evidence does not prove the interpretation is correct.

## Run

Use your existing Python executable:

```powershell
D:\AEGIS\training\.venv\Scripts\python.exe D:\VOICEBRIDGE\app.py
```

Open http://127.0.0.1:8770/ in a browser on this computer and keep the terminal open. For speech, add `--speech-key` and enter the key at the hidden console prompt. No dependencies to install. An occupied port can be changed with `--port 8771`.

The speech upload accepts mono, 16-bit PCM WAV up to 30 seconds. The transcript is editable before saving. Audio is not persisted. Clicks on Transcribe send audio to Gnani and may use credits. No retries are automatic.

The recommended full-demo launcher sets up the verified native Gemini adapter and privately prompts for both keys:

```powershell
D:\AEGIS\training\.venv\Scripts\python.exe D:\VOICEBRIDGE\gemini_setup.py demo --speech-key
```

Enter Gemini first, then Gnani. Open http://127.0.0.1:8775/ and keep the terminal open. Keys remain in process memory; enter them again after restart. Use `app` instead of `demo` for your main workspace. Add `--port 8776` if 8775 is occupied. Gnani credits and Gemini quota/billing are separate.

## Offline checks

```powershell
Set-Location D:\VOICEBRIDGE
D:\AEGIS\training\.venv\Scripts\python.exe -m unittest -v
```

No paid calls are made by these tests. Local database: `local_data/workspace.sqlite3`. Do not expose this development server to the internet. Use synthetic notes for demos.

## Remaining work — fixed release checklist

No additional core features are planned. Three stages remain; checkboxes are pending work, not claimed results.

### 1. Full workflow testing and defect fixes

- [ ] Complete FIRST_USER_TEST.md with both providers in one running demo.
- [ ] Record real Telugu-English speech; check names, quantities, negation and noisy audio. Record original errors before correcting the transcript.
- [ ] Check task extraction and evidence; missing owners/dates must stay unknown until assigned by the user.
- [ ] Have a speaker of the relevant languages review summary/translation meaning, numbers and completeness.
- [ ] Test supported/unsupported questions, contradictory notes and source-text instructions; answers must preserve uncertainty and show useful evidence.
- [ ] Test microphone denial, quota/API errors, empty/long notes and interrupted requests without losing saved work or making automatic retries.
- [ ] Verify corrections/deletion invalidate older outputs, task edits update reports/answers, restart preserves data and backup restoration keeps existing records.
- [ ] Complete the 20-case observation tracker honestly. Fix critical failures; document blocked cases rather than marking them passed.
- [ ] Collect feedback from three potential users and check whether the connected workflow helps their actual work. Do not invent time-saved or adoption claims.
- [ ] Review provider usage/costs, export test results and retain limitations for the demo.

Exit: a working capture → correct → review → tasks → report/Q&A → spoken response flow, with critical failures resolved.

### 2. UI implementation complete; user review pending

- [ ] Agree on the visual direction with the user.
- [x] Replace the long page with clear capture, review, tasks, reports and questions navigation; move release tools out of the primary workflow.
- [x] Improve typography, spacing, icons, recording feedback and draft/reviewed/changed/error states.
- [x] Add purposeful animations and interaction feedback, with reduced-motion support. Show real request states rather than fake progress.
- [x] Make empty/loading/failure/recovery states clear and prevent duplicate pending actions.
- [x] Check keyboard navigation, visible focus, labels, contrast, mobile layout and audio controls.
- [ ] Run the automated/browser suite again after UI changes, then rehearse the live microphone workflow.

Exit: user-approved UI and passing regression checks for the redesigned app.

### 3. Demo and submission

- [ ] Confirm student eligibility and the personal-email exception with Gnani; registration alone does not establish this verification.
- [ ] Prepare code and setup documentation, excluding keys, private databases, audio, backups and personal data from shared files.
- [ ] Include actual test results, architecture, provider roles, limitations and any required asset/open-source attribution.
- [ ] Record a real 60-second working demo using synthetic content. Do not present typed examples or mocks as successful microphone recognition.
- [ ] Explain the audience, connected problems and why Gnani speech matters; avoid unsupported novelty or selection guarantees.
- [ ] User reviews/publishes the video on LinkedIn or X, tags Gnani and includes #GnaniAI and #GreatIndianAIInternshipChallenge.
- [ ] Use the official submission form received through programme communications, nominate the actual public post and save confirmation.
- [ ] Export the preparation checklist and test results; retain a buffer for critical fixes.

Target submission: November 8, 2026. Deadline recorded in programme details: November 10, 2026, 11:59 PM IST. Check the latest rules/form before final submission: https://www.gnani.ai/internship.

The eight preparation-checklist entries are evidence items inside these stages, not missing product features. The app does not verify eligibility or publish/submit anything.

## Limits and deferred scope

Recording: 29 seconds; WAV upload: mono 16-bit PCM, up to 30 seconds. Translation input: 4,000 characters. Readback: 800 characters. Q&A: 1–6 selected sources, up to 24,000 transcript characters. JSON restore: 2.5 MB / 200 sources / 2,000 tasks / 1,200 reviewed notes. Source edits have no undo/history. Exported JSON/Markdown is plaintext. Demo reset clears demo test/checklist observations; export those separately because workspace backups exclude them.

Deferred: payment/order/shipping flows, external messaging, autonomous actions, automatic semantic search across the whole library, translated report layouts, team accounts and public hosting. These are not part of the agreed local-demo release. Hosting would require access controls, secrets management and spending limits first.
