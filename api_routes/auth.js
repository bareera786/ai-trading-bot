// Auth routes: register, login, refresh, logout
const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { getDB, getUserByUsername, createUser, getUserCount } = require('../database_layer/db');
const { verifyToken } = require('./middleware');
const router = express.Router();

// Register: first user is admin
router.post('/register', async (req, res) => {
  const { username, password, email } = req.body;
  if (!username || !password || !email) return res.status(400).json({ error: 'Missing fields' });
  const db = getDB();
  const userCount = await getUserCount();
  const isAdmin = userCount === 0;
  const hash = await bcrypt.hash(password, 10);
  const user = await createUser({ username, email, password: hash, role: isAdmin ? 'ADMIN' : 'USER' });
  res.json({ message: 'User registered', user: { username, email, role: user.role } });
});

// Login
router.post('/login', async (req, res) => {
  const { username, password } = req.body;
  const user = await getUserByUsername(username);
  if (!user) return res.status(401).json({ error: 'Invalid credentials' });
  const valid = await bcrypt.compare(password, user.password);
  if (!valid) return res.status(401).json({ error: 'Invalid credentials' });
  const accessToken = jwt.sign({ id: user.id, role: user.role }, process.env.JWT_SECRET, { expiresIn: '15m' });
  const refreshToken = jwt.sign({ id: user.id, role: user.role }, process.env.JWT_REFRESH_SECRET, { expiresIn: '7d' });
  res.json({ accessToken, refreshToken, user: { id: user.id, username: user.username, role: user.role } });
});

// Refresh
router.post('/refresh', verifyToken, (req, res) => {
  const { id, role } = req.user;
  const accessToken = jwt.sign({ id, role }, process.env.JWT_SECRET, { expiresIn: '15m' });
  res.json({ accessToken });
});

// Logout (client-side: just delete tokens)
router.post('/logout', (req, res) => {
  res.json({ message: 'Logged out' });
});

module.exports = router;
