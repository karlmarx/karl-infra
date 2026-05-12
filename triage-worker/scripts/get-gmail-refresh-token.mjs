#!/usr/bin/env node
// One-shot helper to get a Gmail refresh token using PKCE on localhost:53682.
//
// Usage:
//   GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... node scripts/get-gmail-refresh-token.mjs
//
// Requirements:
//   - The Google OAuth client must be type "Desktop app" OR have
//     http://localhost:53682 as an authorized redirect URI.
//   - Scope: https://www.googleapis.com/auth/gmail.modify
//
// Output: prints the refresh token. Save it via:
//   npx wrangler secret put GOOGLE_REFRESH_TOKEN

import http from "node:http";
import { URL } from "node:url";
import crypto from "node:crypto";

const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars first.");
  process.exit(1);
}

const SCOPE = "https://www.googleapis.com/auth/gmail.modify";
const REDIRECT = "http://localhost:53682";
const STATE = crypto.randomBytes(16).toString("hex");

const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
authUrl.searchParams.set("client_id", CLIENT_ID);
authUrl.searchParams.set("redirect_uri", REDIRECT);
authUrl.searchParams.set("response_type", "code");
authUrl.searchParams.set("scope", SCOPE);
authUrl.searchParams.set("access_type", "offline");
authUrl.searchParams.set("prompt", "consent");
authUrl.searchParams.set("state", STATE);

console.log("\nOpen this URL in a browser and approve:\n");
console.log(authUrl.toString());
console.log("\nWaiting for callback on http://localhost:53682 ...\n");

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, REDIRECT);
  if (url.pathname !== "/") {
    res.writeHead(404);
    res.end();
    return;
  }
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (state !== STATE) {
    res.writeHead(400);
    res.end("state mismatch");
    return;
  }
  if (!code) {
    res.writeHead(400);
    res.end("no code");
    return;
  }

  try {
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        code,
        redirect_uri: REDIRECT,
        grant_type: "authorization_code",
      }),
    });
    const data = await tokenRes.json();
    if (!data.refresh_token) {
      res.writeHead(500);
      res.end("no refresh_token in response — check console");
      console.error("token response:", data);
      server.close();
      process.exit(1);
    }
    res.writeHead(200, { "content-type": "text/plain" });
    res.end("Got it. You can close this tab.");
    console.log("\nRefresh token (save to wrangler secret GOOGLE_REFRESH_TOKEN):\n");
    console.log(data.refresh_token);
    console.log();
    server.close();
    process.exit(0);
  } catch (e) {
    res.writeHead(500);
    res.end(String(e));
    console.error(e);
    server.close();
    process.exit(1);
  }
});

server.listen(53682);
