# Own MCP server on top of lbc

Several Leboncoin MCP servers already exist, so writing another one needs a reason. All of them wrap the same library, `lbc`, which carries the hard part: speaking Leboncoin's mobile API and keeping up with its anti-bot fingerprinting. What they add on top is a few hundred lines of tool definitions, which this project writes itself on the official `mcp` Python SDK, keeping `lbc` for everything Leboncoin-specific.

Owning those lines is what lets the server stay safe to run unattended: dependencies kept current by Renovate, known vulnerabilities audited on every pull request, code and image scanned, and behaviour covered by tests, so that a fix in `lbc` reaches users through a release nobody has to remember. The two existing read-only servers built on `lbc` had no CI at all, and that cannot be added from outside a repository.

## Considered Options

- **Adopt an existing server as is.** Neither of the two read-only ones had dependency updates, audits, tests in CI or image publishing, and both rely on a single maintainer. Neither served streamable HTTP either, which a claude.ai connector needs.
- **Contribute all of it upstream.** It would put every `lbc` fix and every security update behind a maintainer's availability, for code small enough to own.
- **Fork an existing server.** It would mean following upstream by hand, with none of the benefits of owning the code.
- **Talk to Leboncoin directly, without `lbc`.** The anti-bot work is the costly part to maintain, and `lbc` fixes it within days of each break.
