import { launch } from 'chrome-launcher';
import lighthouse from 'lighthouse';
import fs from 'fs';

const url = process.argv[2];
const outputPath = process.argv[3] || 'report.json';

const chrome = await launch({ chromeFlags: ['--headless'] });
const options = { logLevel: 'info', output: 'json', onlyCategories: ['seo'], port: chrome.port };

const runnerResult = await lighthouse(url, options);
fs.writeFileSync(outputPath, runnerResult.report);

await chrome.kill();
