// Robot management routes
const express = require('express');
const { verifyToken, verifyRole } = require('./middleware');
const { startRobot, stopRobot, restartRobot, setStrategy, viewRobotLogs, runStrategy, checkRobotStatus, viewPerformance } = require('../robot_module/robot');
const router = express.Router();

// Admin robot controls
router.post('/start', verifyToken, verifyRole('ADMIN'), (req, res) => res.json({ result: startRobot() }));
router.post('/stop', verifyToken, verifyRole('ADMIN'), (req, res) => res.json({ result: stopRobot() }));
router.post('/restart', verifyToken, verifyRole('ADMIN'), (req, res) => res.json({ result: restartRobot() }));
router.post('/set-strategy', verifyToken, verifyRole('ADMIN'), (req, res) => res.json({ result: setStrategy(req.body.strategy) }));
router.get('/logs', verifyToken, verifyRole('ADMIN'), (req, res) => res.json({ logs: viewRobotLogs() }));

// User robot controls
router.post('/run-strategy', verifyToken, verifyRole('USER'), (req, res) => res.json({ result: runStrategy(req.body.strategy) }));
router.get('/status', verifyToken, verifyRole('USER'), (req, res) => res.json({ status: checkRobotStatus() }));
router.get('/performance', verifyToken, verifyRole('USER'), (req, res) => res.json({ performance: viewPerformance() }));

module.exports = router;
