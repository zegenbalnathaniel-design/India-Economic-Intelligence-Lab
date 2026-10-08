// Bundles src/main.js (+ Hairline) into a static Streamlit custom-component
// directory: index.html + terrain-hero.js + style.css. Streamlit Cloud runs
// Python only, so this build step runs here, once, and its *output*
// (dist/) is what gets committed and served at runtime
// (components.declare_component(path=...)), not re-built on deploy.
import { build } from "esbuild";
import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";

mkdirSync("dist", { recursive: true });

await build({
  entryPoints: ["src/main.js"],
  bundle: true,
  minify: true,
  format: "iife",
  target: ["es2020"],
  outfile: "dist/terrain-hero.js",
});

copyFileSync("src/style.css", "dist/style.css");

writeFileSync(
  "dist/index.html",
  `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<link rel="stylesheet" href="style.css" />
</head>
<body style="margin:0;">
<div id="terrain-hero-root"></div>
<script src="terrain-hero.js"></script>
</body>
</html>
`,
);

console.log("built dist/ (index.html, terrain-hero.js, style.css)");
