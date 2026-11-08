# Development assistance

OpenAI Codex assisted with implementing the poker policy, simulation helper, regression tests, local benchmark runner, source packaging, and documentation. The supplied organizer game rules, evaluator, judge, baseline policies, Dockerfiles, and server routes were retained.

The runtime policy uses ordinary Python/NumPy computation. It makes no calls to Gemini, OpenAI, or any other external service, and requires no API key. No Gemini generations were used for this poker project. The separate Dashboard Royale project's saved Gemini output and billing records are unrelated to the poker bot.

Performance statements refer only to the recorded local test opponents, seeds, source hashes, and environments. Tournament performance and optimal play are not claimed.
