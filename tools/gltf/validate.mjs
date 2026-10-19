import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';

const assetPath = process.argv[2]
  ? path.resolve(process.argv[2])
  : fileURLToPath(new URL('../../export/reef.glb', import.meta.url));
const bytes = new Uint8Array(await fs.readFile(assetPath));
const report = await validator.validateBytes(bytes, {
  uri: path.basename(assetPath),
  maxIssues: 1000,
  externalResourceFunction: async (uri) => {
    throw new Error(`The production GLB must be self-contained: ${uri}`);
  },
});
const output = path.join(path.dirname(assetPath), 'validator.json');
await fs.writeFile(output, JSON.stringify({
  validatorVersion: validator.version(),
  assetSha256: crypto.createHash('sha256').update(bytes).digest('hex'),
  ...report,
}, null, 2) + '\n');
console.log(JSON.stringify({ output, ...report.issues }, null, 2));
if (report.issues.numErrors > 0 || report.issues.truncated) process.exitCode = 1;
