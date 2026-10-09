// Bundles src/main.js (+ Hairline) into a static Streamlit custom-component
// directory, same pattern as app/assets/terrain_hero/build.mjs.
import { build } from "esbuild";
import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";

mkdirSync("dist", { recursive: true });

await build({
  entryPoints: ["src/main.js"],
  bundle: true,
  minify: true,
  format: "iife",
  target: ["es2020"],
  outfile: "dist/turntable.js",
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
<div id="turntable-root"></div>
<script src="turntable.js"></script>
</body>
</html>
`,
);

console.log("built dist/ (index.html, turntable.js, style.css)");
