import { readFileSync } from 'fs';
import { extractTextFromPDFBuffer } from './src/lib/parsers/pdf';

(async () => {
    const filePath = '/home/prak05/Desktop/Anti gravity-code/tarrif.pdf';
    const buffer = readFileSync(filePath);
    try {
        const text = await extractTextFromPDFBuffer(buffer);
        console.log('--- BEGIN TEXT ---');
        console.log(text.slice(0, 2000)); // first 2000 characters
        console.log('--- END TEXT ---');
    } catch (err) {
        console.error('Error extracting PDF:', err);
    }
})();
