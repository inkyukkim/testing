# Blind evaluation round: orchestrator instructions

This branch holds only eight agent workspaces (synthetic data). You are the orchestrator.
Do not do any agent's task yourself and do not read the workspaces' contents beyond each TASK.md.

1. For each directory listed below, read <dir>/TASK.md, replace the line `{WS}` with the absolute
   path of that directory, and launch one subagent (Agent tool, subagent_type general-purpose,
   in the background) with exactly that text as its prompt. Launch all eight, then wait.
   Directories: input-mapper, model-profiler, builder-runner, model-verifier, report-profiler,
   claims-analyst, report-writer, report-verifier.
2. When each subagent finishes, save its final reply verbatim to <dir>/HANDBACK.md.
3. When all eight have finished: `git add -A`, commit with the message
   "Blind evaluation round 3: agent outputs", and push to the branch you were told to push to.
   Do not modify, revert or tidy any file the agents produced, and do not run any tool yourself.
4. Reply with one line per directory: its name and whether a HANDBACK.md was saved.
