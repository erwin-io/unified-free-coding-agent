# Security and no-cost limitations

- Only hardcoded free aliases are routed: kilo-auto/free, openrouter/free,
  gemini-2.5-flash and gemini-2.5-flash-lite.
- The Gemini free tier is specific to your account and project; paid-enabled
  projects could still incur charges. Do not enable paid billing.
- Free services can become unavailable simultaneously. The supervisor must
  stop inference and keep project state; it cannot create free compute.
- Router binds 127.0.0.1, never publish it on a public interface.
- API keys stay in ignored .env. Free providers can retain or train on prompts.
- OpenCode permissions are NOT an operating-system sandbox. Shell runs as you.
  Autonomous auto approval is off by default. Use a disposable test repo
  and restricted Windows user for unattended coding.
- No Git push, deployment or production writes are authorized automatically.
- Owner email is notification only, not an authenticated command channel.
