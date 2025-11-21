// Modular DB layer: SQLite (default), Firebase, MySQL
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
let db;

function initDB() {
  // Default: SQLite
  db = new sqlite3.Database(path.join(__dirname, 'db.sqlite'));
  db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE,
      email TEXT UNIQUE,
      password TEXT,
      role TEXT
    )`);
  });
}
function getDB() { return db; }
function getUserCount() {
  return new Promise((resolve) => {
    db.get('SELECT COUNT(*) as count FROM users', (err, row) => resolve(row.count));
  });
}
function createUser({ username, email, password, role }) {
  return new Promise((resolve, reject) => {
    db.run('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)', [username, email, password, role], function (err) {
      if (err) return reject(err);
      resolve({ id: this.lastID, username, email, role });
    });
  });
}
function getUserByUsername(username) {
  return new Promise((resolve) => {
    db.get('SELECT * FROM users WHERE username = ?', [username], (err, row) => resolve(row));
  });
}
function getUserById(id) {
  return new Promise((resolve) => {
    db.get('SELECT * FROM users WHERE id = ?', [id], (err, row) => resolve(row));
  });
}
function getAllUsers() {
  return new Promise((resolve) => {
    db.all('SELECT id, username, email, role FROM users', (err, rows) => resolve(rows));
  });
}
function updateUser(id, data) {
  const fields = [];
  const values = [];
  for (const key in data) {
    fields.push(`${key} = ?`);
    values.push(data[key]);
  }
  values.push(id);
  return new Promise((resolve) => {
    db.run(`UPDATE users SET ${fields.join(', ')} WHERE id = ?`, values, function (err) {
      resolve({ changes: this.changes });
    });
  });
}
function deleteUser(id) {
  return new Promise((resolve) => {
    db.run('DELETE FROM users WHERE id = ?', [id], function (err) {
      resolve({ changes: this.changes });
    });
  });
}
module.exports = { initDB, getDB, getUserCount, createUser, getUserByUsername, getUserById, getAllUsers, updateUser, deleteUser };
