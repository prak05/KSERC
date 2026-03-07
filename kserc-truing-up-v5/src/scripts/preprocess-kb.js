/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

const kbDir = path.join(__dirname, '../../../knowledge-base');
const dataDir = path.join(__dirname, '../../data');

if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
}

const filesToProcess = {
    new_rules: 'the_electricity_act,_2003.pdf',
    tariff_data: 'Tariff Regulation - 2021_650.pdf',
    historical_data: 'Kanan Devan Hills Plantations Company Private Limited.pdf'
};

async function extractText() {
    console.log("Starting text extraction from knowledge-base PDFs...");
    const extractedData = {};

    for (const [key, filename] of Object.entries(filesToProcess)) {
        const filePath = path.join(kbDir, filename);
        if (fs.existsSync(filePath)) {
            console.log(`Extracting ${filename}...`);
            const dataBuffer = fs.readFileSync(filePath);
            try {
                const data = await pdf(dataBuffer);
                // Keep only the first 5000 characters for context limit purposes, or let's clean it up roughly
                const cleanedText = data.text
                    .replace(/\n\s*\n/g, '\n')
                    .replace(/\s+/g, ' ')
                    .substring(0, 8000); // 8k chars max per section to avoid huge prompts
                extractedData[key] = cleanedText;
                console.log(`Success: extracted ${cleanedText.length} chars for ${key}`);
            } catch (err) {
                console.error(`Error parsing ${filename}:`, err);
                extractedData[key] = `Error extracting ${filename}`;
            }
        } else {
            console.warn(`Warning: File not found ${filePath}`);
            extractedData[key] = 'No content provided.';
        }
    }

    const outputPath = path.join(dataDir, 'rules.json');
    fs.writeFileSync(outputPath, JSON.stringify(extractedData, null, 2));
    console.log(`Saved preprocessed rules to ${outputPath}`);
}

extractText();
