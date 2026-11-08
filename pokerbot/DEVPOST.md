# Devpost entry — DataLarp / SteadyAce

Create a **separate poker project** for the TAMU Datathon event. Keep the Dashboard Royale entry separate. Select the Heads Up challenge wherever the event submission form asks for the challenge or prize category. Complete any additional required fields shown by Devpost.

## Project name

SteadyAce — DataLarp's Heads Up Poker Bot

## Tagline

A fast, reliable Omaha poker bot that weighs hand equity, pot odds, and opponent aggression—even when opponents suddenly go all-in.

## Main project story — copy the sections below

### Inspiration

We wanted to build a poker bot that makes sensible decisions under uncertainty while staying simple enough to trust. In a tournament where repeated errors cause a forfeit, reliability matters as much as strategy.

### What it does

SteadyAce plays heads-up short-deck five-card Pot-Limit Omaha. It chooses among folding, checking/calling, and half-pot or pot raises. It estimates winning chances, compares them with the call price, and adapts its opponent range using observed aggression. Sudden all-ins receive an explicit equity-versus-price decision.

### How we built it

We implemented the three strategy functions in the supplied Python/FastAPI agent. A NumPy helper evaluates simulated hands using exactly two hole cards and three community cards, including the variant's unusual hand rankings. Simulations reuse results when visible cards have not changed. Match-specific memory resets every half. The bot runs offline without API keys or a trained model.

### Challenges we ran into

The main challenges were the eight-second thinking budget, correct Omaha hand construction, and handling aggressive opponents without treating every raise as either a bluff or an unbeatable hand. We tested all-in call prices, tied pots, capped raises, and half resets while preserving the organizer's server plumbing and rules.

### Accomplishments that we're proud of

The submitted version passed 31 tests and won all 21 local duplicate matches across seven practice policies and three seeds: 42,000 hands with zero errors, forfeits, or exhausted time banks. Both native Linux and Linux AMD64 Docker build/smoke checks passed. These are practice results, not tournament results or a guarantee of winning.

### What we learned

Pot odds and expected value provide a useful foundation for decisions under uncertainty. Reproducible match results and compatibility checks are stronger evidence than plausible strategy alone. Our policy uses game-theory-informed heuristics; it is not a solved GTO strategy.

### What's next

Evaluate against more independent opponents and improve opponent-range estimates while preserving the small runtime and reliable action handling.

## Built with

Python, NumPy, FastAPI, Uvicorn, Docker, pytest, GitHub.

Do not list Gemini or Databricks for this poker project: they are not used by the bot.

## AI assistance disclosure

OpenAI Codex assisted with implementation, tests, documentation, and local validation. The playing bot makes no calls to an LLM or external service. See the repository's `pokerbot/AI_DISCLOSURE.md` for details. Include this disclosure in the project story or the event's AI-use field.

## Links and submitted version

- Repository: https://github.com/RedRojoaka/datathon_2026
- Poker project and opening instructions: https://github.com/RedRojoaka/datathon_2026/tree/main/pokerbot
- Submitted bot commit: https://github.com/RedRojoaka/datathon_2026/commit/b3515aade1a437694345a24b93e1d9b5ee643abc
- Strategy at the submitted commit: https://github.com/RedRojoaka/datathon_2026/blob/b3515aade1a437694345a24b93e1d9b5ee643abc/pokerbot/STRATEGY.md
- Validation at the submitted commit: https://github.com/RedRojoaka/datathon_2026/blob/b3515aade1a437694345a24b93e1d9b5ee643abc/pokerbot/VALIDATION.md

If Devpost requests a demo, describe this as a tournament HTTP bot with local run instructions. The repository is not a hosted playable web demo. Follow any required video or gallery fields shown in the event's form; the available source and validation reports can support a walkthrough.

## Finish the submission

1. Add the project name, tagline, story, technologies, and repository link.
2. Add the correct team members and select the Heads Up challenge/category if offered.
3. Include the AI-assistance disclosure and any required event fields.
4. Publish/submit the project to the event and verify that it is submitted, not only saved as a draft.
5. Keep the bot commit already entered in the separate tournament submission form: `b3515aade1a437694345a24b93e1d9b5ee643abc`. Adding Devpost documentation does not require changing that form's SHA.
