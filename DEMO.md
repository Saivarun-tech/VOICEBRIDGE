# Submission rehearsal

Use a separate synthetic workspace:

```powershell
D:\AEGIS\training\.venv\Scripts\python.exe D:\VOICEBRIDGE\app.py --demo --port 8774
```

Open http://127.0.0.1:8774/. To test live providers, also add `--speech-key --reasoning-setup`; keys are entered privately and stay in memory. No reasoning provider has been verified yet.

Demo mode uses `local_data/demo.sqlite3`; normal mode uses `local_data/workspace.sqlite3`. It seeds three clearly labelled Telugu-English notes (handover, customer request, service update). These are written examples, not captured audio or model output. Tasks and reviewed summaries start empty. Reset requires confirmation and only exists in demo mode; it clears that demo workspace and reseeds the samples.

Suggested 60-second recording after live checks pass: show the problem (0–10s), capture and correct Telugu-English speech (10–25s), review a task and its evidence (25–40s), export a report and ask about pending work (40–50s), play the spoken answer and show honest test results (50–60s). Record actual working output. Do not present typed examples, mocks or prerecorded synthetic speech as real microphone performance.

No further core feature expansion is planned. Required next steps are live model verification, user tests, UI redesign and submission assets. Current local preview/demo does not establish that the project is submitted or eligible verification is complete.
