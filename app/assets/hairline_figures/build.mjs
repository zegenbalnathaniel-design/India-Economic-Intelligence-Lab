// Bundles three Hairline figures (slow, elevator, vault) into static
// Streamlit-servable directories: dist/<name>/{index.html,bundle.js,style.css}.
// Same pattern as app/assets/terrain_hero/build.mjs -- built offline with
// esbuild since Streamlit Cloud runs Python only; dist/ is the committed,
// already-built artifact.
import { build } from "esbuild";
import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";

const FIGURES = ["slow", "elevator", "vault"];

for (const name of FIGURES) {
  mkdirSync(`dist/${name}`, { recursive: true });

  await build({
    entryPoints: [`src/${name}.js`],
    bundle: true,
    minify: true,
    format: "iife",
    target: ["es2020"],
    outfile: `dist/${name}/bundle.js`,
  });

  copyFileSync("src/shared.css", `dist/${name}/style.css`);

  writeFileSync(
    `dist/${name}/index.html`,
    `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<link rel="stylesheet" href="style.css" />
</head>
<body style="margin:0;">
<div id="figure-root"></div>
<script src="bundle.js"></script>
</body>
</html>
`,
  );
}

console.log("built dist/{slow,elevator,vault}/");
