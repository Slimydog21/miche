import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8799",
    trace: "on-first-retry",
  },
  webServer: {
    command:
      "rm -f logs/e2e_island_thread.jsonl logs/e2e_island_utterance.jsonl && uv run uvicorn miche.web:app --host 127.0.0.1 --port 8799",
    url: "http://127.0.0.1:8799/api/health",
    reuseExistingServer: true,
    env: {
      MICHE_ISLAND_ROUTER_FIXTURE: "cassette",
      MICHE_ISLAND_THREAD_PATH: "logs/e2e_island_thread.jsonl",
      MICHE_ISLAND_UTTERANCE_LOG: "logs/e2e_island_utterance.jsonl",
    },
  },
});