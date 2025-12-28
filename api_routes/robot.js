// Robot management routes
const express = require('express');
const { verifyToken, verifyRole, rateLimit } = require('./middleware');
const { startRobot, stopRobot, restartRobot, setStrategy, viewRobotLogs, runStrategy, checkRobotStatus, viewPerformance } = require('../robot_module/robot');
const router = express.Router();

// Apply rate limiting to all routes
router.use(rateLimit(50, 15 * 60 * 1000)); // 50 requests per 15 minutes

// Admin robot controls
router.post('/start', verifyToken, verifyRole('ADMIN'), (req, res) => {
  try {
    const result = startRobot();
    res.json({ result, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

router.post('/stop', verifyToken, verifyRole('ADMIN'), (req, res) => {
  try {
    const result = stopRobot();
    res.json({ result, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

router.post('/restart', verifyToken, verifyRole('ADMIN'), (req, res) => {
  try {
    const result = restartRobot();
    res.json({ result, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

router.post('/set-strategy', verifyToken, verifyRole('ADMIN'), (req, res) => {
  try {
    const result = setStrategy(req.body.strategy);
    res.json({ result, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

router.get('/logs', verifyToken, verifyRole('ADMIN'), (req, res) => {
  try {
    const logs = viewRobotLogs();
    res.json({ logs, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

// User robot controls
router.post('/run-strategy', verifyToken, verifyRole('USER'), (req, res) => {
  try {
    const result = runStrategy(req.body.strategy);
    res.json({ result, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

router.get('/status', verifyToken, verifyRole('USER'), (req, res) => {
  try {
    const status = checkRobotStatus();
    res.json({ status, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

router.get('/performance', verifyToken, verifyRole('USER'), (req, res) => {
  try {
    const performance = viewPerformance();
    res.json({ performance, success: true });
  } catch (error) {
    res.status(500).json({ error: error.message, success: false });
  }
});

module.exports = router;
