import { Hono } from "hono";
import { neon } from "@neondatabase/serverless";

type Env = {
  Bindings: {
    DATABASE_URL?: string;
    APP_ENV?: string;
    ADMIN_EMAIL?: string;
    OTP_EXPIRY_SECONDS?: string;
    RESEND_API_KEY?: string;
  };
};

const app = new Hono<Env>();
const OTP_COOKIE = "swp_admin_challenge";
const SESSION_COOKIE = "swp_admin_session";
const OTP_LENGTH = 6;
const DEFAULT_OTP_TTL = 300;
const SESSION_TTL_SECONDS = 10 * 60 * 60;

function cookieOptions(maxAge: number) {
  return `Path=/; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Strict`;
}
function randomDigits(): string {
  const bytes = new Uint8Array(OTP_LENGTH);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => String(b % 10)).join("");
}
function randomToken(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
async function digest(value: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}
function ttl(env: Env["Bindings"]): number {
  const parsed = Number(env.OTP_EXPIRY_SECONDS);
  return Number.isInteger(parsed) && parsed >= 60 && parsed <= 900 ? parsed : DEFAULT_OTP_TTL;
}
async function ensureTables(sql: any) {
  await sql`CREATE TABLE IF NOT EXISTS swp_admin_otp_challenges (
    challenge_id text PRIMARY KEY,
    otp_digest text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    attempts integer NOT NULL DEFAULT 0,
    consumed boolean NOT NULL DEFAULT false
  )`;
  await sql`CREATE TABLE IF NOT EXISTS swp_admin_sessions (
    token_digest text PRIMARY KEY,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
  )`;
}

app.get("/health", (c) => c.json({ status: "ok", service: "swp-homes-api" }));

app.get("/api/v1/health/database", async (c) => {
  if (!c.env.DATABASE_URL) return c.json({ status: "not_configured" }, 503);
  try {
    const sql = neon(c.env.DATABASE_URL);
    await sql`select 1 as healthy`;
    return c.json({ status: "ok", database: "reachable" });
  } catch {
    return c.json({ status: "unavailable" }, 503);
  }
});

// Admin login intentionally exposes a single OTP field—no username or password.
app.get("/", (c) => c.html(`<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SWP-HOMES | دخول المدير</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#eef2f7;font-family:Tahoma,Arial,sans-serif;color:#17243a}
main{width:min(92vw,420px);background:white;border-radius:18px;padding:32px;box-shadow:0 12px 40px #14213d18}h1{font-size:24px;margin:0 0 8px}p{color:#65738a;line-height:1.8}label{display:block;margin:24px 0 8px;font-weight:bold}
input{width:100%;padding:14px;border:1px solid #ccd5e2;border-radius:10px;font-size:24px;letter-spacing:8px;text-align:center}
button{width:100%;padding:13px;margin-top:14px;border:0;border-radius:10px;background:#173b70;color:white;font-size:16px;cursor:pointer}button.secondary{background:#e8edf5;color:#173b70}
#status{min-height:28px;font-size:14px} </style></head><body><main>
<h1>SWP-HOMES</h1><p>دخول مدير النظام — أدخل رمز التحقق المرسل إلى البريد الإلكتروني المسجل.</p>
<form id="form"><label for="otp">رمز OTP</label><input id="otp" name="otp" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required autofocus>
<button type="submit">تحقق ودخول</button></form><button id="resend" class="secondary" type="button">إعادة إرسال الرمز</button><p id="status" role="status"></p>
<script>
const statusEl=document.getElementById('status'), otp=document.getElementById('otp');
async function send(){statusEl.textContent='جارٍ إرسال رمز التحقق…';try{const r=await fetch('/api/v1/admin/otp/request',{method:'POST'});const d=await r.json();statusEl.textContent=r.ok?'تم إرسال الرمز إلى البريد المسجل.':(d.error||'تعذر إرسال الرمز.');}catch{statusEl.textContent='تعذر الاتصال بالخدمة.'}}
document.getElementById('form').addEventListener('submit',async e=>{e.preventDefault();if(!/^[0-9]{6}$/.test(otp.value)){statusEl.textContent='أدخل رمزًا مكونًا من 6 أرقام.';return}statusEl.textContent='جارٍ التحقق…';try{const r=await fetch('/api/v1/admin/otp/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({otp:otp.value})});const d=await r.json();statusEl.textContent=r.ok?'تم التحقق بنجاح. جلسة المدير مفعلة.':(d.error||'رمز غير صحيح أو منتهي.');if(r.ok){otp.value='';}}catch{statusEl.textContent='تعذر الاتصال بالخدمة.'}});
document.getElementById('resend').addEventListener('click',send);send();
</script></main></body></html>`));

app.post("/api/v1/admin/otp/request", async (c) => {
  const { DATABASE_URL, ADMIN_EMAIL, RESEND_API_KEY } = c.env;
  if (!DATABASE_URL || !ADMIN_EMAIL || !RESEND_API_KEY) {
    return c.json({ error: "admin_otp_not_configured" }, 503);
  }
  try {
    const sql = neon(DATABASE_URL);
    await ensureTables(sql);
    const prior = await sql`SELECT created_at FROM swp_admin_otp_challenges WHERE consumed=false AND expires_at > now() ORDER BY created_at DESC LIMIT 1`;
    if (prior.length && Date.now() - new Date(String(prior[0].created_at)).getTime() < 60_000) {
      return c.json({ error: "please_wait_before_resending" }, 429);
    }
    const code = randomDigits();
    const challengeId = randomToken();
    await sql`INSERT INTO swp_admin_otp_challenges (challenge_id, otp_digest, expires_at, attempts, consumed)
      VALUES (${challengeId}, ${await digest(code)}, now() + (${ttl(c.env)} * interval '1 second'), 0, false)`;
    const emailResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: "SWP-HOMES <onboarding@resend.dev>",
        to: [ADMIN_EMAIL],
        subject: "رمز دخول مدير النظام - SWP-HOMES",
        text: `رمز التحقق الخاص بك: ${code}\nصلاحية الرمز ${ttl(c.env)} ثانية. لا تشارك الرمز مع أي شخص.`,
      }),
    });
    if (!emailResponse.ok) {
      await sql`UPDATE swp_admin_otp_challenges SET consumed=true WHERE challenge_id=${challengeId}`;
      return c.json({ error: "email_delivery_failed" }, 502);
    }
    c.header("Set-Cookie", `${OTP_COOKIE}=${challengeId}; ${cookieOptions(ttl(c.env))}`);
    c.header("Cache-Control", "no-store");
    return c.json({ status: "sent" });
  } catch {
    return c.json({ error: "otp_request_failed" }, 503);
  }
});

app.post("/api/v1/admin/otp/verify", async (c) => {
  const { DATABASE_URL } = c.env;
  const challengeId = c.req.header("Cookie")?.split(";").map((part) => part.trim())
    .find((part) => part.startsWith(`${OTP_COOKIE}=`))?.slice(OTP_COOKIE.length + 1);
  if (!DATABASE_URL || !challengeId) return c.json({ error: "challenge_missing" }, 401);
  let body: { otp?: unknown };
  try { body = await c.req.json(); } catch { return c.json({ error: "invalid_request" }, 400); }
  if (typeof body.otp !== "string" || !/^[0-9]{6}$/.test(body.otp)) {
    return c.json({ error: "invalid_otp_format" }, 400);
  }
  try {
    const sql = neon(DATABASE_URL);
    await ensureTables(sql);
    const rows = await sql`SELECT otp_digest, expires_at, attempts, consumed FROM swp_admin_otp_challenges WHERE challenge_id=${challengeId} LIMIT 1`;
    if (!rows.length || rows[0].consumed || new Date(String(rows[0].expires_at)).getTime() <= Date.now() || Number(rows[0].attempts) >= 5) {
      return c.json({ error: "otp_expired_or_locked" }, 401);
    }
    if (await digest(body.otp) !== String(rows[0].otp_digest)) {
      await sql`UPDATE swp_admin_otp_challenges SET attempts=attempts+1 WHERE challenge_id=${challengeId}`;
      return c.json({ error: "invalid_otp" }, 401);
    }
    const sessionToken = randomToken();
    await sql`UPDATE swp_admin_otp_challenges SET consumed=true WHERE challenge_id=${challengeId}`;
    await sql`INSERT INTO swp_admin_sessions (token_digest, expires_at) VALUES (${await digest(sessionToken)}, now() + (10 * interval '1 hour'))`;
    c.header("Set-Cookie", `${SESSION_COOKIE}=${sessionToken}; ${cookieOptions(SESSION_TTL_SECONDS)}`);
    c.header("Set-Cookie", `${OTP_COOKIE}=; ${cookieOptions(0)}`, { append: true });
    c.header("Cache-Control", "no-store");
    return c.json({ status: "verified" });
  } catch {
    return c.json({ error: "otp_verification_failed" }, 503);
  }
});

app.get("/api/v1/admin/session", async (c) => {
  const token = c.req.header("Cookie")?.split(";").map((part) => part.trim())
    .find((part) => part.startsWith(`${SESSION_COOKIE}=`))?.slice(SESSION_COOKIE.length + 1);
  if (!token || !c.env.DATABASE_URL) return c.json({ authenticated: false }, 401);
  try {
    const sql = neon(c.env.DATABASE_URL);
    await ensureTables(sql);
    const rows = await sql`SELECT token_digest FROM swp_admin_sessions WHERE token_digest=${await digest(token)} AND expires_at > now() LIMIT 1`;
    return rows.length ? c.json({ authenticated: true, role: "admin" }) : c.json({ authenticated: false }, 401);
  } catch {
    return c.json({ authenticated: false }, 503);
  }
});

app.notFound((c) => c.json({ error: "not_found" }, 404));
export default app;
