Start Claude Code in this folder, then copy everything below the line and paste it in. Edit the
bracketed parts first.

---

We're starting the Reflection Lab project in this folder. Read CLAUDE.md and README.md first: they hold
the goal, the rules and the plan.

Goal for today: set everything up and run the first real test of the analyst → critic → refiner loop on
this machine ([your OS, CPU, RAM, GPU and VRAM]).

Work through the phases in CLAUDE.md in order:
1. Check what is installed and what is missing (bootstrap.ps1 on Windows, bootstrap.sh on Linux/macOS,
   then the environment report). Ask me before installing anything outside the project's .venv.
2. Find the models I already have. My model folders are [list them, or "none"]. If they are outside the
   project, put them in config.local.toml (copy config.local.example.toml). Never move, copy or delete
   my files.
3. Download the models that are missing (Gemma 4 E4B and Qwen3 1.7B as .litertlm). Show me the file
   names and sizes first and wait for my OK.
4. Test the pipeline with the fake model, then a 2-case smoke test with the real models, then a full
   run on tests/cases.jsonl.

I want to see what is going on:
- Before each command, tell me in one line what it does.
- Run long jobs (scans, downloads, experiments) in a separate window (open_window.ps1 on Windows) so I
  can watch the live view, and keep me updated from the log files.
- After each phase, give me a short summary: what worked, what failed, what's next.

If something fails (GPU backend, memory, API differences), explain it simply, try the fallback listed in
CLAUDE.md, and tell me what you changed.
