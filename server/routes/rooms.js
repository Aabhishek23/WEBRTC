const express = require('express');
const router = express.Router();
const { generateRoomId, roomExists } = require('../utils/roomIdGenerator');

/**
 * POST /api/rooms
 * Creates a new room and returns a unique 9-digit room ID (XXX-XXX-XXX)
 */
router.post('/', (req, res, next) => {
  try {
    const roomId = generateRoomId();

    res.status(201).json({
      success: true,
      roomId,
      message: 'Room created successfully',
      createdAt: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/rooms/:roomId
 * Check if a room exists
 */
router.get('/:roomId', (req, res, next) => {
  try {
    const { roomId } = req.params;
    const exists = roomExists(roomId);

    if (!exists) {
      return res.status(404).json({
        success: false,
        message: `Room ${roomId} not found`,
      });
    }

    res.status(200).json({
      success: true,
      roomId,
      message: 'Room exists',
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
