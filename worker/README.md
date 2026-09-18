# AI Worker for the Publish tab

A tiny Cloudflare Worker the desktop app calls to write YouTube titles, descriptions and
hashtags. It tries providers in order and returns the first answer:

1. **Workers AI** (free daily allowance, no key): `@cf/openai/gpt-oss-120b`, then
   `@cf/meta/llama-3.3-70b-instruct-fp8-fast`
2. **Claude** (`claude-opus-5`), only if `ANTHROPIC_API_KEY` is set
3. **Gemini** (`gemini-2.5-flash`), only if `GEMINI_API_KEY` is set

API keys stay on Cloudflare; the app only knows the Worker URL and a shared app token.
Credits and the rights statement are added by the app itself, never by the model.

## Deploy (once)

Needs a free Cloudflare account and Node.js.

```bash
cd worker
npm install
npx wrangler login                     # opens the browser to sign in to Cloudflare
npx wrangler secret put APP_TOKEN      # paste any long random string; the app uses it too
npx wrangler deploy                    # prints https://persian-lyric-sync-ai.<you>.workers.dev
```

Then in the app: **Publish tab → AI settings…**, paste the URL and the same token,
and press **Test connection**.

## Later: add Claude or Gemini

```bash
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put GEMINI_API_KEY
```

No redeploy is needed for secrets. Change the order or models in `wrangler.toml`
(`PROVIDER_ORDER`, `WORKERS_AI_MODELS`, `CLAUDE_MODEL`, `GEMINI_MODEL`) and run
`npx wrangler deploy` again.

## Test

```bash
npm test        # unit tests with a fake Workers AI binding (no account needed)
curl https://persian-lyric-sync-ai.<you>.workers.dev/   # {"ok":true,"providers":[...]}
```
