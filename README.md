# Social Promo Studio (phases 1 and 2: drafting + Facebook/Instagram posting)

Desktop app that drafts per-platform social posts for your apps (Siddhanta, ClearIQ, SleepRise, ...)
with Gemini (or local Ollama), validates them in code, and lets you edit and copy them.
Posts to Instagram (Instagram Login API, no Facebook Page needed) and Facebook Pages. X, Reddit draft-assist and
scheduling arrive in phase 3 (see the project wiki). Reddit and X cards are copy-only for now.

## Run
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python -m promo_studio
```
Linux may need `sudo apt install python3-tk`.

## First use
1. **Settings**: choose the provider, check the Gemini model name (model names change; use one shown in
   Google AI Studio), paste your Gemini API key, click *Test AI connection*.
2. **Profiles**: create one profile per app (pitch, audience, features, tone, store links, banned phrases).
3. **Compose**: pick app + angle, optionally add a base idea, note and image, press *Generate with AI*
   (Ctrl+Enter; the button becomes *Cancel* while it waits). Use `<` `>` to browse variants, edit, then
   *Copy* into the platform. If a text is over the limit, *Shorten* asks the AI to rewrite it and the code
   re-checks the length. Drafts auto-save every 30 s (and on close, or Ctrl+S) and come back on next launch;
   *Clear all* wipes them.
4. **Posting**: connect accounts first (`docs/SETUP_META.md`), then *Preview all* and *Post now* (Ctrl+Shift+Enter).
   Each platform reports its own result; *Retry* re-sends only the failed one. A post that may have gone out but
   could not be confirmed is flagged *unconfirmed* and is never retried automatically.
5. **Profiles**: *Export* / *Import* share or back up all profiles as JSON (import merges by name).

Data lives in `%APPDATA%\PromoStudio` (Windows) or `~/.promo_studio`: `promo_studio.db`, `app.log`.
API keys go to the OS keyring (fallback: `.env` in that folder). Override the folder with `PROMO_STUDIO_HOME`.

## Tests
```bash
python -m pytest -q
```

## Layout
```
promo_studio/
  ai/         provider interface, Gemini, Ollama, prompts
  core/       validators, draft service, publisher, image service/host, rate limiter, context
  adapters/   Facebook, Instagram, shared Graph API error handling
  data/       SQLite schema, models
  config/     settings, secrets
  ui/         Compose, Profiles, Settings tabs
tests/
```

## Phase status
- [x] Phase 1: profiles (+JSON import/export), settings, Gemini/Ollama drafting, validation, Shorten, Cancel,
      draft auto-save, log redaction, Compose UI (26 unit tests + headless UI smoke tests)
- [x] Phase 2: Facebook + Instagram adapters, Pillow image crops, ImgBB temp hosting, parallel Publisher with
      retries and duplicate protection, Preview/Post now/Retry UI, token refresh (69 unit tests + UI smoke tests)
      NOT yet verified against the live Meta APIs: needs your credentials (see docs/SETUP_META.md)
- [ ] Phase 3: X, Reddit draft-assist, scheduler, Queue and History
- [ ] Phase 4: ASO tab, backups, packaging
