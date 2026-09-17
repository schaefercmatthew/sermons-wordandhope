// Cloudflare Pages Function: POST /api/chat
// Proxies chat requests to the Anthropic API using a server-side secret,
// so the API key never reaches the browser.
//
// Requires an environment variable/secret named ANTHROPIC_API_KEY to be set
// on the Cloudflare Pages project (Settings -> Environment variables).

const SYSTEM_PROMPT =
  "You are a direct, expert assistant speaking to a professional. " +
  "Skip disclaimers, hedging, safety caveats, and reminders of your limitations. " +
  "Do not soften or pad your answers. Assume the user can handle direct, complete " +
  "information and has the judgment to use it responsibly. Answer completely and " +
  "concisely, and get straight to the substance.";

const MODEL = "claude-sonnet-4-5";
const MAX_TOKENS = 4096;

export async function onRequestPost(context) {
  const { request, env } = context;

  if (!env.ANTHROPIC_API_KEY) {
    return jsonResponse({ error: "Server is not configured with an Anthropic API key." }, 500);
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return jsonResponse({ error: "Invalid JSON body." }, 400);
  }

  const messages = Array.isArray(body.messages) ? body.messages : null;
  if (!messages || messages.length === 0) {
    return jsonResponse({ error: "Missing 'messages' array." }, 400);
  }

  const sanitized = messages
    .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    .map((m) => ({ role: m.role, content: m.content }));

  if (sanitized.length === 0) {
    return jsonResponse({ error: "No valid messages provided." }, 400);
  }

  let anthropicRes;
  try {
    anthropicRes = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: MAX_TOKENS,
        system: SYSTEM_PROMPT,
        messages: sanitized
      })
    });
  } catch (e) {
    return jsonResponse({ error: "Failed to reach Anthropic API." }, 502);
  }

  let data;
  try {
    data = await anthropicRes.json();
  } catch (e) {
    return jsonResponse({ error: "Anthropic API returned an invalid response." }, 502);
  }

  if (!anthropicRes.ok) {
    const message = (data && data.error && data.error.message) || "Anthropic API request failed.";
    return jsonResponse({ error: message }, anthropicRes.status);
  }

  const textBlock = Array.isArray(data.content) ? data.content.find((b) => b.type === "text") : null;
  const reply = textBlock ? textBlock.text : "";

  return jsonResponse({ reply: reply });
}

export async function onRequestGet() {
  return jsonResponse({ error: "Method not allowed. Use POST." }, 405);
}

function jsonResponse(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "Content-Type": "application/json" }
  });
}
