#!/usr/bin/env python3
"""
Basic tests for the simulation mode of Meebo components
"""
import os
import sys
import unittest
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sensors.sensor_manager import SensorManager
from src.actuators.motor_controller import MotorController
from src.vision.camera_manager import CameraManager
from src.audio.audio_manager import AudioManager


class TestSimulationMode(unittest.TestCase):
    """Test the simulation mode of various components."""

    def setUp(self):
        """Set up test environment."""
        # Force simulation mode
        os.environ["MEEBO_DEV_MODE"] = "true"

    def test_sensor_simulation(self):
        """Test that sensor simulation works."""
        sensor_manager = SensorManager(simulation_mode=True)
        readings = sensor_manager.get_all_readings()
        
        # Check that we get some readings
        self.assertIn("ir_sensors", readings)
        self.assertIn("distance", readings)
        self.assertIn("timestamp", readings)
        
        # Check IR sensor format
        ir_readings = readings["ir_sensors"]
        self.assertIn("front_left", ir_readings)
        self.assertIn("front_right", ir_readings)
        self.assertIn("rear_left", ir_readings)
        self.assertIn("rear_right", ir_readings)
        
        # Check distance reading
        self.assertIsInstance(readings["distance"], float)
        
        # Clean up
        sensor_manager.cleanup()

    def test_motor_simulation(self):
        """Test that motor simulation works."""
        motor_controller = MotorController(simulation_mode=True)
        
        # Test movement commands
        motor_controller.move_forward(50)
        status = motor_controller.get_status()
        
        self.assertEqual(status["left"]["speed"], 50)
        self.assertEqual(status["right"]["speed"], 50)
        self.assertEqual(status["left"]["direction"], 1)
        self.assertEqual(status["right"]["direction"], 1)
        
        # Test stop
        motor_controller.stop_all()
        status = motor_controller.get_status()
        
        self.assertEqual(status["left"]["speed"], 0)
        self.assertEqual(status["right"]["speed"], 0)
        self.assertEqual(status["left"]["direction"], 0)
        self.assertEqual(status["right"]["direction"], 0)

    def test_camera_simulation(self):
        """Test that camera simulation works."""
        camera_manager = CameraManager(simulation_mode=True)
        
        # Get a frame
        frame_info = camera_manager.get_frame()
        
        # Check basic frame info
        self.assertIn("timestamp", frame_info)
        self.assertIn("frame_count", frame_info)
        self.assertIn("resolution", frame_info)
        self.assertIn("has_frame", frame_info)
        
        # Check for simulated objects
        self.assertIn("objects_detected", frame_info)
        
        # Clean up
        camera_manager.release()

    def test_audio_simulation(self):
        """Test that audio simulation works."""
        audio_manager = AudioManager(simulation_mode=True)
        
        # Test text-to-speech
        result = audio_manager.say("Hello, robot world")
        self.assertTrue(result)
        
        # Test listening for a command
        command = audio_manager.listen_for_command(timeout=1.0)
        # Just verify it returns a string (may be empty if simulation doesn't recognize)
        self.assertIsInstance(command, str)
        
        # Clean up
        audio_manager.cleanup()


if __name__ == "__main__":
    unittest.main() 