/**
 * i18n key completeness checker
 * Compares en.json, hi.json, and mr.json to ensure all keys are present in all files.
 * Usage: node scripts/check-i18n.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get all keys from a nested object
function getAllKeys(obj, prefix = '') {
  const keys = [];
  for (const key in obj) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === 'object' && obj[key] !== null) {
      keys.push(...getAllKeys(obj[key], fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys.sort();
}

// Load and parse JSON file
function loadJson(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error.message);
    return null;
  }
}

// Main check
const localesDir = path.join(__dirname, '../src/i18n/locales');
const en = loadJson(path.join(localesDir, 'en.json'));
const hi = loadJson(path.join(localesDir, 'hi.json'));
const mr = loadJson(path.join(localesDir, 'mr.json'));

if (!en || !hi || !mr) {
  console.error('Failed to load one or more locale files');
  process.exit(1);
}

const enKeys = new Set(getAllKeys(en));
const hiKeys = new Set(getAllKeys(hi));
const mrKeys = new Set(getAllKeys(mr));

// Find missing keys
const missingInHi = [...enKeys].filter(k => !hiKeys.has(k));
const missingInMr = [...enKeys].filter(k => !mrKeys.has(k));
const extraInHi = [...hiKeys].filter(k => !enKeys.has(k));
const extraInMr = [...mrKeys].filter(k => !enKeys.has(k));

let hasErrors = false;

console.log('=== i18n Key Completeness Check ===\n');

if (missingInHi.length > 0) {
  console.log(`❌ Missing ${missingInHi.length} keys in hi.json:`);
  missingInHi.forEach(k => console.log(`   - ${k}`));
  console.log('');
  hasErrors = true;
} else {
  console.log('✅ hi.json has all keys from en.json\n');
}

if (missingInMr.length > 0) {
  console.log(`❌ Missing ${missingInMr.length} keys in mr.json:`);
  missingInMr.forEach(k => console.log(`   - ${k}`));
  console.log('');
  hasErrors = true;
} else {
  console.log('✅ mr.json has all keys from en.json\n');
}

if (extraInHi.length > 0) {
  console.log(`⚠️  ${extraInHi.length} extra keys in hi.json (not in en.json):`);
  extraInHi.forEach(k => console.log(`   - ${k}`));
  console.log('');
}

if (extraInMr.length > 0) {
  console.log(`⚠️  ${extraInMr.length} extra keys in mr.json (not in en.json):`);
  extraInMr.forEach(k => console.log(`   - ${k}`));
  console.log('');
}

console.log(`Total keys in en.json: ${enKeys.size}`);
console.log(`Total keys in hi.json: ${hiKeys.size}`);
console.log(`Total keys in mr.json: ${mrKeys.size}`);

if (hasErrors) {
  console.log('\n❌ Check failed: Missing translation keys found');
  process.exit(1);
} else {
  console.log('\n✅ All translation keys are complete across all languages');
  process.exit(0);
}
