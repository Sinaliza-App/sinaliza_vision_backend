require('dotenv').config();
const pool = require('./db');
const fs = require('fs');
const path = require('path');

async function migrateV3() {
  console.log('--- Iniciando Migração V3: RBAC & Coleta de Dados ---');
  let client;
  try {
    client = await pool.connect();
    const sqlPath = path.join(__dirname, 'v3_coleta_rbac.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');
    
    await client.query(sql);
    console.log('✅ Migração V3 aplicada com sucesso no banco de dados!');
  } catch (err) {
    console.error('❌ Erro ao executar migração V3:', err.message);
  } finally {
    if (client) client.release();
    await pool.end();
  }
}

migrateV3();
