import express from "express";
import { createServer as createViteServer } from "vite";
import Database from "better-sqlite3";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const db = new Database("kserc.db");

// Initialize Database Schema
db.exec(`
  CREATE TABLE IF NOT EXISTS licensees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    short_code TEXT NOT NULL UNIQUE
  );

  CREATE TABLE IF NOT EXISTS historical_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    licensee_code TEXT,
    financial_year TEXT,
    claimed_lakhs REAL,
    approved_lakhs REAL,
    outcome_type TEXT,
    notes TEXT
  );

  CREATE TABLE IF NOT EXISTS analysis_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    licensee_id INTEGER,
    financial_year TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

// Seed Licensees if empty
const licenseesCount = db.prepare("SELECT COUNT(*) as count FROM licensees").get() as { count: number };
if (licenseesCount.count === 0) {
  const insert = db.prepare("INSERT INTO licensees (name, short_code) VALUES (?, ?)");
  insert.run('Kanan Devan Hills Plantations Company Pvt Ltd', 'KDHPCL');
  insert.run('Electronics Technology Parks – Kerala, Technopark', 'TECHNOPARK');
  insert.run('Infoparks Kerala', 'INFOPARK');
  insert.run('Cochin Special Economic Zone Authority', 'CSEZA');
}

// Seed Historical Data if empty
const historyCount = db.prepare("SELECT COUNT(*) as count FROM historical_orders").get() as { count: number };
if (historyCount.count === 0) {
  const insert = db.prepare("INSERT INTO historical_orders (licensee_code, financial_year, claimed_lakhs, approved_lakhs, outcome_type, notes) VALUES (?, ?, ?, ?, ?, ?)");
  insert.run('TECHNOPARK', '2020-21', null, 280.42, 'SURPLUS', 'Highest surplus on record');
  insert.run('CSEZA', '2022-23', null, 135.14, 'SURPLUS', null);
  insert.run('KDHPCL', '2022-23', null, 116.91, 'SURPLUS', null);
  insert.run('CSEZA', '2023-24', -3.42, 87.85, 'REVERSAL', 'Claimed deficit, Commission found surplus');
  insert.run('KDHPCL', '2021-22', 13.61, 58.72, 'OVERSHOOT', 'Commission approved 4x what was asked');
  insert.run('INFOPARK', '2020-21', -76.53, -60.80, 'GAP', '15.73L disallowed');
  insert.run('INFOPARK', '2024-25', -79.76, -64.72, 'GAP', '15.04L disallowed');
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API Routes
  app.get("/api/licensees", (req, res) => {
    const rows = db.prepare("SELECT * FROM licensees").all();
    res.json(rows);
  });

  app.get("/api/history", (req, res) => {
    const rows = db.prepare("SELECT * FROM historical_orders").all();
    res.json(rows);
  });

  app.post("/api/calculate", (req, res) => {
    const { approved_arr, actual_revenue } = req.body;
    const gap = approved_arr - actual_revenue;
    const outcome = gap > 0 ? "GAP" : "SURPLUS";
    const is_anomaly = gap > 64.72 || gap < -280.42;
    
    res.json({
      gap_amount: Number(gap.toFixed(4)),
      outcome,
      is_anomaly,
      message: `₹${Math.abs(gap).toFixed(2)} Lakh ${outcome}`
    });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(__dirname, "dist")));
    app.get("*", (req, res) => {
      res.sendFile(path.join(__dirname, "dist", "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
