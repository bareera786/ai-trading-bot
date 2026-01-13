import { build } from 'esbuild';
import fs from 'node:fs/promises';
import path from 'node:path';
import url from 'node:url';

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const staticDir = path.join(projectRoot, 'app', 'static');
const distDir = path.join(staticDir, 'dist');
const manifestPath = path.join(distDir, 'manifest.json');

const entryDefinitions = [
  { key: 'dashboard', logical: 'dashboard.js', source: path.join(staticDir, 'src', 'js', 'dashboard', 'index.js') },
  { key: 'dashboard-styles', logical: 'dashboard.css', source: path.join(staticDir, 'css', 'dashboard.css') },
  { key: 'auth-styles', logical: 'auth.css', source: path.join(staticDir, 'src', 'css', 'auth.css') },
  { key: 'subscription-card', logical: 'subscription-card.js', source: path.join(staticDir, 'js', 'subscription-card.js') },
  { key: 'lead-capture', logical: 'lead-capture.js', source: path.join(staticDir, 'js', 'lead-capture.js') },
  { key: 'admin-leads', logical: 'admin-leads.js', source: path.join(staticDir, 'js', 'admin-leads.js') }
];

const entryPoints = Object.fromEntries(entryDefinitions.map((entry) => [entry.key, entry.source]));

async function ensureDistDir() {
  await fs.mkdir(distDir, { recursive: true });
}

async function deleteOldDashboardBundles() {
  try {
    const entries = await fs.readdir(distDir, { withFileTypes: true });
    await Promise.all(
      entries
        .filter((ent) => ent.isFile() && ent.name.startsWith('dashboard-'))
        .map((ent) => fs.unlink(path.join(distDir, ent.name)))
    );
  } catch (error) {
    // If dist doesn't exist yet or cleanup fails, proceed with build.
  }
}

function createPathLookup() {
  return new Map(entryDefinitions.map((entry) => [path.resolve(entry.source), entry.logical]));
}

async function writeManifest(manifest) {
  await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
}

function relativizeOutput(outputPath) {
  return path.relative(staticDir, path.resolve(outputPath)).replace(/\\/g, '/');
}

async function buildAssets() {
  await ensureDistDir();
  // Prevent stale dashboard bundles from accumulating. Keep only the newest
  // dashboard hash per build by removing any existing dashboard-* files first.
  await deleteOldDashboardBundles();

  const buildId = new Date().toISOString();
  process.env.BUILD_ID = buildId;

  const result = await build({
    entryPoints,
    bundle: true,
    outdir: distDir,
    entryNames: '[name]-[hash]',
    chunkNames: 'chunks/[name]-[hash]',
    assetNames: 'assets/[name]-[hash]',
    metafile: true,
    sourcemap: false,
    minify: true,
    target: ['es2019'],
    platform: 'browser',
    format: 'esm',
    splitting: false,
    define: {
      BUILD_ID: JSON.stringify(buildId),
    },
    loader: {
      '.css': 'css'
    }
  });

  const pathLookup = createPathLookup();
  const manifest = {};

  for (const [outfile, metadata] of Object.entries(result.metafile.outputs || {})) {
    if (!metadata.entryPoint) {
      continue;
    }
    const logical = pathLookup.get(path.resolve(metadata.entryPoint));
    if (!logical) {
      continue;
    }
    manifest[logical] = relativizeOutput(outfile);
  }

  await writeManifest(manifest);
  // Validate generated manifest files are usable (non-zero size).
  const zeroFiles = [];
  for (const [logical, relPath] of Object.entries(manifest)) {
    const abs = path.join(staticDir, relPath);
    try {
      const st = await fs.stat(abs);
      if (!st.size) {
        zeroFiles.push({ logical, path: abs });
      }
    } catch (err) {
      zeroFiles.push({ logical, path: abs });
    }
  }
  if (zeroFiles.length) {
    console.error('Build validation failed: some generated assets are zero-length or missing:');
    for (const f of zeroFiles) {
      console.error(` - ${f.logical} -> ${f.path}`);
    }
    // Exit with non-zero to fail CI / build processes.
    process.exitCode = 2;
    throw new Error('One or more generated assets are zero-length or missing');
  }
  console.log('Built assets:', JSON.stringify(manifest, null, 2));
}

buildAssets().catch((error) => {
  console.error('Asset build failed:', error);
  process.exitCode = 1;
});
