import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      "react-hooks/set-state-in-effect": "off",
      // M-16: bloquear rehype-raw (desactiva el sanitizado XSS de react-markdown)
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["rehype-raw", "rehype-raw/*"],
              message:
                "rehype-raw desactiva el sanitizado XSS de react-markdown. Usa rehype-sanitize en su lugar.",
            },
          ],
        },
      ],
      // M-16: bloquear dangerouslySetInnerHTML en JSX
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message:
            "dangerouslySetInnerHTML está prohibido. Usa react-markdown con rehype-sanitize.",
        },
      ],
    },
  },
]);
