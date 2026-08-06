import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
// `vitest/config` rather than `vite` so the `test` block below is actually read.
import { defineConfig } from "vitest/config";

const here = (relativePath: string) =>
  fileURLToPath(new URL(relativePath, import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "~": here("./src"),
      // capybara_2d_engine is self-hosted from source (third_party/…/PROVENANCE.md);
      // it publishes no build output, so the client compiles its TypeScript directly.
      "@capybara": here("../../third_party/capybara_2d_engine/src"),
    },
  },
  server: {
    // MapGen.Api binds loopback only and its CORS allows exactly these dev origins.
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
