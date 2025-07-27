// run_lighthouse.mjs

import { launch } from 'chrome-launcher';
import lighthouse from 'lighthouse';
import fs from 'fs';

// URL und optionaler Ausgabe-Pfad als CLI-Args
const url = process.argv[2];
const outputPath = process.argv[3] || 'report.json';

// Den in Dockerfile definierten Chromium-Pfad nutzen, falls gesetzt
const chromePath = process.env.CHROME_PATH || undefined;

(async () => {
  // 1) Chromium headless + no-sandbox starten
  const chrome = await launch({
    chromePath,
    chromeFlags: ['--headless', '--no-sandbox']
  });

  // 2) Lighthouse nur für die SEO-Kategorie ausführen
  const options = {
    logLevel: 'info',
    output: 'json',
    onlyCategories: ['seo'],
    port: chrome.port
  };
  const runnerResult = await lighthouse(url, options);

  // 3) Report als JSON schreiben (lhr enthält das vollständige Ergebnisobjekt)
  const reportJson = runnerResult.lhr;
  fs.writeFileSync(outputPath, JSON.stringify(reportJson, null, 2));

  // 4) Chrome-Prozess beenden
  await chrome.kill();
})();
