import { Hono } from "hono";
import { neon } from "@neondatabase/serverless";

type Env = {
  Bindings: {
    DATABASE_URL?: string;
    APP_ENV?: string;
  };
};

const app = new Hono<Env>();

app.get("/health", (c) => c.json({ status: "ok", service: "swp-homes-api" }));

app.get("/api/v1/health/database", async (c) => {
  const connectionString = c.env.DATABASE_URL;
  if (!connectionString) {
    return c.json({ status: "not_configured" }, 503);
  }

  try {
    const sql = neon(connectionString);
    await sql`select 1 as healthy`;
    return c.json({ status: "ok", database: "reachable" });
  } catch {
    // Do not return connection strings, SQL details, or provider errors to clients.
    return c.json({ status: "unavailable" }, 503);
  }
});

app.notFound((c) => c.json({ error: "not_found" }, 404));

export default app;
