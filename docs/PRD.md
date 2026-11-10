# ARES v0.1 — Product Requirements Document

Status: approved for build | Date: 10 November 2026 | Source: `ARES_Project_Report.md` plus the review of it

## 1. Product

ARES is a local, free assistant that operates a Windows 11 laptop from spoken or typed commands. The user says "Aries" (or presses a hotkey, or types), gives a command, sees what ARES is about to do, and ARES does it. Nothing leaves the device.

**Target machine:** Intel i5-1335U, 16 GB RAM, integrated graphics. **Budget:** zero. **Team:** one builder.

## 2. Goals and non-goals

Goals for v0.1:

1. Common commands run in about a second without a language model.
2. No action can damage data without an explicit, previewed confirmation, and file actions can be undone.
3. ARES gets faster with use: phrases resolved once by the model are remembered.
4. The whole core is usable and testable by typing, with voice as an optional layer on top.

Non-goals for v0.1 (deferred, with reasons):

| Deferred | Reason |
|---|---|
| Calendar | Needs Google/Microsoft sign-in; provider not yet chosen |
| "Build me a project" | Coding agents are paid or need a cloud model; a folder is not a real sandbox |
| In-app UI Automation, numbered click overlay, teach-by-demonstration | Next release; needs the core first |
| Tauri orb | v0.1 uses a small Tk orb (standard library, no build chain) |
| macOS, Linux, phones, cloud fallback, multi-user | Out of scope |

## 3. Users and core stories

Primary user: a power user or student on their own laptop.

- As a user I say or type "open notepad" and it opens at once.
- As a user I say "volume to 30" and it changes without asking me, and "undo" puts it back.
- As a user I say "delete report.txt in downloads"; ARES shows exactly what will go to the Recycle Bin and waits for my yes.
- As a user I say something vague ("make it quieter in here"); the local model picks a tool, I confirm, and next time the same phrase is instant.
- As a user I press the stop hotkey or say/type "stop" and everything pending is cancelled.
- As a user I can read a log of everything ARES did.

## 4. Functional requirements

| ID | Requirement |
|---|---|
| F1 | Text interface (`ares` REPL and one-shot `ares "command"`) drives the same engine as voice |
| F2 | Rule-based router maps phrases to tool calls without a model (fast path) |
| F3 | Learned fast path: a confirmed model resolution is stored and reused for the same normalised phrase |
| F4 | Slow path: local model via Ollama chooses one tool from a shortlist of the most relevant tools, with output constrained to JSON; if Ollama is absent ARES says so and carries on |
| F5 | Every tool has a risk tier, a permission group and a plain-language preview |
| F6 | Risk policy (section 5) is enforced in one place, for every tool call, whatever produced it |
| F7 | File tools work only inside allowed folders, checked on the fully resolved path |
| F8 | Deletes go to the Recycle Bin, never permanent |
| F9 | Action log (time, phrase, tool, arguments, result) and an undo stack in SQLite; "undo" reverts the last undoable action |
| F10 | Permission groups (files, apps, browser, system, microphone) are all off until the user enables them; stored in a config file |
| F11 | "stop" / "cancel" clears any pending confirmation and halts speech, in every state |
| F12 | Voice loop: wake word, end-of-speech detection, speech to text, spoken reply, with a push-to-talk hotkey and a stop hotkey |
| F13 | While ARES is speaking the microphone is ignored except for the stop hotkey (no echo cancellation in v0.1) |
| F14 | Orb shows idle, listening, thinking, working, speaking, and the pending confirmation text |
| F15 | Voice and Windows dependencies are optional; the core imports and runs without them |

## 5. Risk policy

| Tier | Behaviour | Examples |
|---|---|---|
| `read_only` | Run immediately | open app, open URL, time, show folder |
| `auto_reversible` | Run immediately, push an undo entry | volume, mute, brightness, theme |
| `reversible` | One confirmation, push an undo entry | create, move, rename |
| `destructive` | Preview of exactly what changes, then explicit confirmation; more than 10 files is refused | delete to Recycle Bin, close window |
| `forbidden` | Never run; hand back to the user | passwords, payments, security settings |

Rules: deny by default; only registered tools run; text read from files or the web is never treated as a command; arguments are passed to the operating system as data, never spliced into a command string; no telemetry.

## 6. v0.1 command catalogue

| Command | Tool | Tier |
|---|---|---|
| open / launch an app | `open_app` | read_only |
| go to a website | `open_url` | read_only |
| search the web | `web_search` | read_only |
| time and date | `clock` | read_only |
| show a folder | `open_folder` | read_only |
| read a text file | `read_file` | read_only |
| list a folder | `list_folder` | read_only |
| volume to N / up / down | `set_volume` | auto_reversible |
| mute / unmute | `set_mute` | auto_reversible |
| brightness to N | `set_brightness` | auto_reversible |
| dark / light mode | `set_theme` | auto_reversible |
| minimise everything | `show_desktop` | auto_reversible |
| take a screenshot | `screenshot` | auto_reversible |
| create a folder | `create_folder` | reversible |
| create a note | `create_file` | reversible |
| move a file | `move_file` | reversible |
| rename a file | `rename_file` | reversible |
| remind me in N minutes | `reminder` | reversible |
| delete a file | `delete_files` | destructive |
| close the active window | `close_window` | destructive |
| undo, stop, help, show log | built into the engine | — |

## 7. Architecture

One Python process with threads (not six processes): simpler for one builder; split later only if measurements demand it.

```
voice loop / orb / CLI  ->  Engine.handle_text(text)
                              router (rules -> learned -> model)
                              safety (permission, tier, allowed folders, confirm)
                              tool handler -> Platform (Windows | Fake)
                              store (SQLite: log, undo, learned phrases, memory)
```

- `ares.core.contracts` — the shared types every module builds on.
- `ares.core` — router, safety, store, brain (Ollama client), engine.
- `ares.platform` — `Platform` interface, `WindowsPlatform`, `FakePlatform` for tests.
- `ares.tools` — one module per group; each registers tools.
- `ares.voice` — wake word (openWakeWord), VAD, speech to text (faster-whisper), speech (Windows built-in voice by default), hotkeys.
- `ares.ui` — Tk orb.
- `ares.cli` — entry point.

Core has no third-party dependencies. Voice and Windows extras are optional installs.

## 8. Quality targets (to be measured on the target laptop)

| Target | Value |
|---|---|
| Fast-path routing accuracy | at least 95% on the catalogue with 4 phrasings each |
| Unconfirmed destructive actions | zero, enforced by tests |
| Fast path, text in to action | under 100 ms excluding the tool itself |
| Fast path by voice, end of speech to action | about 1.5 s median |
| Model tool choice | at least 90% on a 50-command set |
| Idle RAM | measure and record; no fixed promise in v0.1 |

## 9. Acceptance for v0.1

1. `pytest` passes on any OS using `FakePlatform`.
2. On Windows, every catalogue command works from the text REPL.
3. Safety tests prove: no destructive run without confirmation, no file access outside allowed folders, "stop" clears pending actions, undo restores.
4. Voice mode starts, wakes, transcribes and speaks on the target laptop.

## 10. Open questions

1. Languages beyond English (Hindi, Telugu)? Changes the speech model.
2. Calendar provider?
3. Which three apps should get in-app control first?
