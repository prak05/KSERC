import fs from 'fs';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '.local-db.json');

interface LocalDatabase {
    licensees: any[];
    truing_cases: any[];
    cost_heads: any[];
    revenue_data: any[];
}

function initDb() {
    if (!fs.existsSync(DB_PATH)) {
        const defaultData: LocalDatabase = {
            licensees: [
                { id: 'lic-1', name: 'Infoparks Kerala', short_name: 'Infoparks' },
                { id: 'lic-2', name: 'Electronics Technology Parks – Kerala', short_name: 'Technopark' },
                { id: 'lic-3', name: 'Kanan Devan Hills Plantations Company', short_name: 'KDHP' },
                { id: 'lic-4', name: 'Cochin Special Economic Zone Authority', short_name: 'CSEZA' },
            ],
            truing_cases: [],
            cost_heads: [],
            revenue_data: []
        };
        fs.writeFileSync(DB_PATH, JSON.stringify(defaultData, null, 2), 'utf8');
    }
}

function readDb(): LocalDatabase {
    initDb();
    const rawData = fs.readFileSync(DB_PATH, 'utf8');
    return JSON.parse(rawData);
}

function writeDb(data: LocalDatabase) {
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf8');
}

export const db = {
    getLicenseeByShortName: (shortName: string) => {
        const data = readDb();
        // Default to the first if custom name used
        return data.licensees.find(l => l.short_name === shortName) || data.licensees[0];
    },

    insertCase: (caseRecord: any) => {
        const data = readDb();
        const id = `case-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        const newCase = { ...caseRecord, id, created_at: new Date().toISOString() };
        data.truing_cases.push(newCase);
        writeDb(data);
        return newCase;
    },

    updateCase: (id: string, updates: any) => {
        const data = readDb();
        const index = data.truing_cases.findIndex(c => c.id === id);
        if (index !== -1) {
            data.truing_cases[index] = { ...data.truing_cases[index], ...updates };
            writeDb(data);
        }
    },

    getCase: (id: string) => {
        const data = readDb();
        const caseObj = data.truing_cases.find(c => c.id === id);
        if (!caseObj) return null;
        const licensee = data.licensees.find(l => l.id === caseObj.licensee_id);
        return { ...caseObj, licensees: licensee };
    },

    insertCostHeads: (heads: any[]) => {
        const data = readDb();
        const newHeads = heads.map(h => ({
            ...h,
            id: `ch-${Date.now()}-${Math.floor(Math.random() * 10000)}`
        }));
        data.cost_heads.push(...newHeads);
        writeDb(data);
        return newHeads;
    },

    updateCostHead: (id: string, updates: any) => {
        const data = readDb();
        const index = data.cost_heads.findIndex(ch => ch.id === id);
        if (index !== -1) {
            data.cost_heads[index] = { ...data.cost_heads[index], ...updates };
            writeDb(data);
        }
    },

    getCostHeads: (caseId: string) => {
        const data = readDb();
        return data.cost_heads.filter(ch => ch.case_id === caseId);
    },

    getCostHead: (id: string) => {
        const data = readDb();
        return data.cost_heads.find(ch => ch.id === id) || null;
    },

    insertRevenueData: (revData: any) => {
        const data = readDb();
        const newRev = {
            ...revData,
            id: `rev-${Date.now()}-${Math.floor(Math.random() * 1000)}`
        };
        data.revenue_data.push(newRev);
        writeDb(data);
        return newRev;
    },

    getRevenueData: (caseId: string) => {
        const data = readDb();
        return data.revenue_data.find(r => r.case_id === caseId) || null;
    },

    deleteCase: (caseId: string) => {
        const data = readDb();
        data.truing_cases = data.truing_cases.filter(c => c.id !== caseId);
        data.cost_heads = data.cost_heads.filter(ch => ch.case_id !== caseId);
        data.revenue_data = data.revenue_data.filter(r => r.case_id !== caseId);
        writeDb(data);
        return true;
    }
};
