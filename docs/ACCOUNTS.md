# Accounts and API keys

1. Kilo Gateway: anonymous Auto Free can work without a key.
   Optional account https://app.kilo.ai/ and KILO_API_KEY.
2. Gemini API: https://aistudio.google.com/api-keys
   Create GEMINI_API_KEY in a project eligible for the free API tier.
   Verify account-specific limits. Do NOT enable paid billing.
3. OpenRouter: https://openrouter.ai/settings/keys
   Create OPENROUTER_API_KEY. Free router uses openrouter/free,
   normally 50 requests/day on unfunded free accounts.
4. Owner email (optional): dedicated Gmail account with 2FA and a supported
   app password for SMTP. Configure SMTP_USERNAME, SMTP_APP_PASSWORD,
   EMAIL_FROM, OWNER_EMAIL, EMAIL_ENABLED=true.
   The supervisor sends outbound status/approval-request emails only.
   Email replies are NOT processed as commands.

Store real keys only in local .env, never in Git, issues, or chat.
