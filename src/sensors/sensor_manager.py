import logging
import random
import time
from typing import Dict, Any, List, Optional

from src.config.settings import SENSORS
from src.utils.logger import SimulatedLogger

logger = logging.getLogger(__name__)

class SensorManager:
    """
    Manager for all robot sensors. Handles both real and simulated sensors.
    Provides a unified interface for getting sensor readings.
    """
    
    def __init__(self, simulation_mode=False):
        """
        Initialize the sensor manager.
        
        Args:
            simulation_mode (bool): Whether to use simulated sensors.
        """
        self.simulation_mode = simulation_mode
        
        if simulation_mode:
            self.sim_logger = SimulatedLogger("sensors")
            self.sim_logger.info("Initializing simulated sensors")
        else:
            logger.info("Initializing physical sensors")
            
        # Initialize sensors
        self._init_ir_sensors()
        self._init_ultrasonic_sensor()
        
        logger.info(f"Sensor manager initialized (simulation: {simulation_mode})")
    
    def _init_ir_sensors(self):
        """Initialize IR sensors."""
        self.ir_pins = SENSORS["ir_sensors"]
        
        if not self.simulation_mode:
            try:
                # In real mode, set up the actual GPIO
                # This would be replaced with actual GPIO setup code
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                for pin in self.ir_pins:
                    GPIO.setup(pin, GPIO.IN)
                logger.info(f"IR sensors initialized on pins {self.ir_pins}")
            except ImportError:
                logger.warning("RPi.GPIO not available, falling back to simulation mode for IR sensors")
                self.simulation_mode = True
        
    def _init_ultrasonic_sensor(self):
        """Initialize ultrasonic sensor."""
        self.ultrasonic = SENSORS["ultrasonic"]
        
        if not self.simulation_mode:
            try:
                # In real mode, set up the actual GPIO
                # This would be replaced with actual GPIO setup code
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.ultrasonic["trig_pin"], GPIO.OUT)
                GPIO.setup(self.ultrasonic["echo_pin"], GPIO.IN)
                logger.info(f"Ultrasonic sensor initialized on pins: "
                           f"TRIG={self.ultrasonic['trig_pin']}, "
                           f"ECHO={self.ultrasonic['echo_pin']}")
            except ImportError:
                logger.warning("RPi.GPIO not available, falling back to simulation mode for ultrasonic sensor")
                self.simulation_mode = True
    
    def get_ir_readings(self) -> Dict[str, bool]:
        """
        Get readings from all IR sensors.
        
        Returns:
            Dict[str, bool]: Dictionary with sensor name as key and boolean value
                             (True if obstacle detected, False otherwise)
        """
        if self.simulation_mode:
            # Simulate random IR readings
            readings = {}
            directions = ["front_left", "front_right", "rear_left", "rear_right"]
            for i, direction in enumerate(directions):
                # 20% chance of obstacle detection in simulation
                readings[direction] = random.random() < 0.2
                
            self.sim_logger.debug(f"Simulated IR readings: {readings}")
            return readings
        else:
            # Real hardware readings
            try:
                import RPi.GPIO as GPIO
                readings = {}
                directions = ["front_left", "front_right", "rear_left", "rear_right"]
                for i, pin in enumerate(self.ir_pins):
                    # IR sensors typically return LOW (0) when obstacle detected
                    # So we invert the reading for a more intuitive API
                    readings[directions[i]] = not GPIO.input(pin)
                
                logger.debug(f"IR readings: {readings}")
                return readings
            except Exception as e:
                logger.error(f"Error reading IR sensors: {str(e)}")
                return {"error": str(e)}
    
    def get_distance(self) -> float:
        """
        Get distance reading from ultrasonic sensor.
        
        Returns:
            float: Distance in centimeters.
        """
        if self.simulation_mode:
            # Simulate random distance between 5 and 200 cm
            distance = random.uniform(5, 200)
            self.sim_logger.debug(f"Simulated distance: {distance:.2f} cm")
            return distance
        else:
            # Real hardware reading
            try:
                import RPi.GPIO as GPIO
                import time
                
                # Set trigger to HIGH
                GPIO.output(self.ultrasonic["trig_pin"], True)
                # Wait 10 microseconds
                time.sleep(0.00001)
                # Set trigger to LOW
                GPIO.output(self.ultrasonic["trig_pin"], False)
                
                # Save start time
                start_time = time.time()
                # Save end time
                stop_time = time.time()
                
                # Record time when echo starts
                while GPIO.input(self.ultrasonic["echo_pin"]) == 0:
                    start_time = time.time()
                    # Timeout if no echo received
                    if time.time() - stop_time > 0.1:
                        return float('inf')
                
                # Record time when echo arrives
                while GPIO.input(self.ultrasonic["echo_pin"]) == 1:
                    stop_time = time.time()
                    # Timeout if echo is too long
                    if time.time() - start_time > 0.1:
                        return float('inf')
                
                # Calculate distance (speed of sound = 34300 cm/s)
                # Time is in seconds, so distance is in cm
                # Divide by 2 because sound travels to object and back
                time_elapsed = stop_time - start_time
                distance = (time_elapsed * 34300) / 2
                
                logger.debug(f"Distance: {distance:.2f} cm")
                return distance
            except Exception as e:
                logger.error(f"Error reading ultrasonic sensor: {str(e)}")
                return float('inf')  # Return infinity on error
    
    def get_all_readings(self) -> Dict[str, Any]:
        """
        Get readings from all sensors.
        
        Returns:
            Dict[str, Any]: Dictionary with all sensor readings.
        """
        readings = {
            "ir_sensors": self.get_ir_readings(),
            "distance": self.get_distance(),
            "timestamp": time.time()
        }
        
        return readings
    
    def cleanup(self):
        """Clean up GPIO pins and other resources."""
        if not self.simulation_mode:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                logger.info("GPIO cleanup completed")
            except Exception as e:
                logger.error(f"Error during GPIO cleanup: {str(e)}")
        else:
            self.sim_logger.info("Simulated sensors cleanup completed") 