// User management routes (admin only for CRUD, user for profile)
const express = require('express');
const { getDB, getAllUsers, getUserById, updateUser, deleteUser } = require('../database_layer/db');
const { verifyToken, verifyRole } = require('./middleware');
const router = express.Router();

// Get all users (admin only)
router.get('/', verifyToken, verifyRole('ADMIN'), async (req, res) => {
  const users = await getAllUsers();
  res.json({ users });
});

// Get user by ID (admin only)
router.get('/:id', verifyToken, verifyRole('ADMIN'), async (req, res) => {
  const user = await getUserById(req.params.id);
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json({ user });
});

// Update user (admin only)
router.put('/:id', verifyToken, verifyRole('ADMIN'), async (req, res) => {
  const updated = await updateUser(req.params.id, req.body);
  res.json({ updated });
});

// Delete user (admin only)
router.delete('/:id', verifyToken, verifyRole('ADMIN'), async (req, res) => {
  const deleted = await deleteUser(req.params.id);
  res.json({ deleted });
});

// User profile (user only)
router.get('/profile/me', verifyToken, verifyRole('USER'), async (req, res) => {
  const user = await getUserById(req.user.id);
  res.json({ user });
});

router.put('/profile/me', verifyToken, verifyRole('USER'), async (req, res) => {
  const updated = await updateUser(req.user.id, req.body);
  res.json({ updated });
});

module.exports = router;
