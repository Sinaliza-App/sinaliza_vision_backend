const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function run() {
  const client = await pool.connect();
  try {
    const res = await client.query(`SELECT * FROM modules ORDER BY id;`);
    console.log("Modules:");
    console.table(res.rows);
    const res2 = await client.query(`SELECT * FROM lessons ORDER BY id;`);
    console.log("Lessons:");
    console.table(res2.rows.map(r => ({id: r.id, title: r.title, module_id: r.module_id})));
  } finally {
    client.release();
    pool.end();
  }
}
run();
