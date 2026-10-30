# GitHub access in the Unified Agent host

Your ChatGPT GitHub connector is NOT automatically shared with other models,
OpenCode, Kilo, Gemini, or the local router.

Recommended host-level integration: the official GitHub CLI (gh).
This provides local machine authentication independent of the cloud model:
1. One-time install, if needed: winget install --id GitHub.cli -e
2. One-time interactive login: double-click CONNECT-GITHUB.bat
3. Verify access: powershell -File scripts/github-access.ps1 -Action status
4. The target project needs a correct Git origin remote for repo-specific actions.

The local agent can inspect GitHub data through the authenticated GitHub CLI
if its shell permissions permit. Never use gh auth token, show token output, or
send credentials to an AI model. GitHub OAuth login may have broad account
permissions, so restrict account/repository scopes where practical.

For stronger isolation use a GitHub App with read-only permissions and a
local broker enforcing allowed operations; this is NOT yet implemented.
An OpenCode shell capable of arbitrary commands is not the same thing as
an isolated read-only GitHub integration. Use protected branches and manual
approvals to enforce no merges to main.

Temporary PR workflow:
- Agent works on local agent/TASK-ID branch.
- Supervisor writes Tech Lead review packet and pauses.
- Owner inspects actual code/tests and asks ChatGPT for review.
- Only after owner authorization should a branch be pushed and a PR opened.
- GitHub required reviews/status checks must protect main.
- No automatic publishing or merging is done by this repository.

For GitHub branch protection, configure your target repository's
Settings -> Rules -> Rulesets to require a pull request, passing checks and
review before merge. ChatGPT manual verdict is NOT a GitHub approval.
