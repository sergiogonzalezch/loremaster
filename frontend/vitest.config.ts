import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "happy-dom",
      setupFiles: ["./src/test/setup.ts"],
      globals: true,
      coverage: {
        provider: "v8",
        include: ["src/utils/**", "src/hooks/**", "src/components/**"],
        exclude: ["src/pages/**", "src/types/**", "src/api/**"],
      },
    },
  }),
);
