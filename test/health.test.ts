import { describe, expect, it } from "vitest";
import worker from "../src/index";

describe("SWP-HOMES Worker health", () => {
  it("returns a public liveness response without database configuration", async () => {
    const response = await worker.fetch(
      new Request("https://example.test/health"),
      { APP_ENV: "test" },
      {} as never
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: "ok",
      service: "swp-homes-api"
    });
  });

  it("does not claim database health when the secret is absent", async () => {
    const response = await worker.fetch(
      new Request("https://example.test/api/v1/health/database"),
      { APP_ENV: "test" },
      {} as never
    );
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ status: "not_configured" });
  });
});
