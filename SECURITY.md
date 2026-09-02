# Security Policy

ACE-S is a context-selection skill. It does not require secrets, API keys, a background service, or privileged network access by itself.

## Supported versions

ACE-S is currently a public research alpha. Security-relevant fixes are applied to the latest `main` branch and documented in the changelog when appropriate.

## Reporting a vulnerability

Please do **not** publish exploit details in a public issue when the report could expose users to prompt-injection, data-exfiltration, privilege-boundary, or unsafe tool-use risks.

Use GitHub's private vulnerability reporting/security advisory flow for this repository when available. If that path is unavailable, open a minimal public issue requesting a private contact channel without including exploit details.

Useful report information includes:

- affected ACE-S version/commit;
- agent/runtime and tools in use;
- minimal reproduction steps;
- expected vs observed behavior;
- whether untrusted retrieved content influenced tool use or instruction priority;
- impact and any known mitigation.

## Security model

ACE-S treats retrieved content, repository text, web pages, tool output, logs, and historical messages as **evidence/data unless the host agent explicitly grants them instruction authority**.

Implementations should preserve these boundaries:

1. untrusted retrieved content must not silently override system/developer/user instructions;
2. context optimization must not bypass tool permissions or confirmation requirements;
3. summaries must not launder untrusted instructions into trusted control state;
4. source provenance should be retained for security-relevant claims;
5. exact security contracts/policies should use raw authoritative evidence rather than lossy summaries.

ACE-S is not a sandbox and does not replace the host runtime's security controls.
