const { v4: uuidv4 } = require('uuid');

// In-memory store to prevent duplicate room IDs
const activeRooms = new Set();

/**
 * Generates a unique 9-digit room ID in XXX-XXX-XXX format
 * @returns {string} Unique room ID
 */
const generateRoomId = () => {
  let roomId;

  do {
    // Generate 9 random digits and format as XXX-XXX-XXX
    const digits = Math.floor(100000000 + Math.random() * 900000000).toString();
    roomId = `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6, 9)}`;
  } while (activeRooms.has(roomId)); // Ensure no duplicates

  activeRooms.add(roomId);
  return roomId;
};

/**
 * Remove a room from active store (when room is closed)
 * @param {string} roomId
 */
const removeRoom = (roomId) => {
  activeRooms.delete(roomId);
};

/**
 * Check if a room exists
 * @param {string} roomId
 * @returns {boolean}
 */
const roomExists = (roomId) => activeRooms.has(roomId);

module.exports = { generateRoomId, removeRoom, roomExists, activeRooms };
