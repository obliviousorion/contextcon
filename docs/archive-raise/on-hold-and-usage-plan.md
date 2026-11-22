# On hold + Claude usage plan

## On hold (not done yet)
1. Pre-mortem council: agents imagine Raise lost, then list the failure points.
2. Pitch deck, 4 slides: hook, problem, eval proof, architecture + business.
3. Ready-to-paste first prompts for the 3 coding agents (A: client/cache/watch, B: pipeline/ranking/eval, C: frontend).
4. 8:30 AM go/no-go reminder for hackathon day.

A reminder is scheduled in the chat for 9:00 PM IST tonight.

## How the limits work
- The 5-hour window starts at your first message. It resets in full 5 hours later.
- There is also a weekly limit.
- Claude and Claude Code share the same limits.
- Usage grows with conversation length, model choice and effort level.
- Check Settings > Usage for your next reset time, your weekly remaining usage, and any limit resets you can use.

## Hackathon-day timing (9 AM–9 PM)
| Window | Starts | Use it for |
|---|---|---|
| W1 | **~6:30 AM**: send one small message, e.g. "good morning, go/no-go checklist", to start the clock | 9:00–11:30: API checks, contracts, kick off the coding agents |
| W2 | ~11:30 AM, at the reset | Heaviest build: pipeline, ranking, citations, UI wiring |
| W3 | ~4:30 PM | Eval runs, watcher, demo recording, pitch polish, last fixes |

If you have a limit reset in Settings > Usage, save it for W2 or W3. Don't spend it tonight.

## Rules to make usage go further
- **Start a fresh chat in the ContextCon project tomorrow.** This chat is very long, and every message here re-sends all of it. The project docs carry the context.
- **Split work across tools.** Give the frontend agent (C) and boilerplate to Antigravity, which has a separate quota. Keep Claude Code for the hard logic: ranking, citations, eval, debugging.
- **Pick model and effort per task.** Use Sonnet or low effort for routine code. Use Opus or high effort only for tricky logic and debugging.
- **In Claude Code:** point it at SPEC.md instead of re-explaining. Run `/clear` between unrelated tasks. Keep one focused task per session.
- **No councils or subagents on build day.** They are expensive. Do the planning tonight.
- **The LLM calls inside Raise run on your Anthropic API key**, not your subscription. Cache them too.
- **Tonight:** keep usage light, since the weekly limit carries over to tomorrow. Do only the held items you really need.
