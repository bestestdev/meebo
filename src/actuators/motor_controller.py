import logging
import time
from typing import Dict, Any, Optional, Tuple

from src.config.settings import MOTORS
from src.utils.logger import SimulatedLogger

logger = logging.getLogger(__name__)

class MotorController:
    """
    Controller for robot motors. Handles both real and simulated motors.
    Provides a unified interface for controlling motor movement.
    """
    
    def __init__(self, simulation_mode=False):
        """
        Initialize the motor controller.
        
        Args:
            simulation_mode (bool): Whether to use simulated motors.
        """
        self.simulation_mode = simulation_mode
        self.motor_config = MOTORS
        
        # Current speeds (0-100)
        self.speeds = {
            "left": 0,
            "right": 0
        }
        
        # Current directions (1 for forward, -1 for backward, 0 for stopped)
        self.directions = {
            "left": 0,
            "right": 0
        }
        
        if simulation_mode:
            self.sim_logger = SimulatedLogger("motors")
            self.sim_logger.info("Initializing simulated motors")
        else:
            logger.info("Initializing physical motors")
            self._init_physical_motors()
            
        logger.info(f"Motor controller initialized (simulation: {simulation_mode})")
    
    def _init_physical_motors(self):
        """Initialize the physical motor control hardware."""
        try:
            # Initialize GPIO
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            
            # Initialize the L298N pins
            for motor in ["left_motor", "right_motor"]:
                GPIO.setup(self.motor_config[motor]["in1_pin"], GPIO.OUT)
                GPIO.setup(self.motor_config[motor]["in2_pin"], GPIO.OUT)
                
            # Initialize PWM controller
            try:
                import adafruit_pca9685
                import board
                import busio
                
                # Initialize I2C bus
                i2c = busio.I2C(board.SCL, board.SDA)
                
                # Initialize PCA9685
                self.pwm = adafruit_pca9685.PCA9685(i2c)
                self.pwm.frequency = 60  # Set PWM frequency to 60Hz
                
                logger.info("PWM controller initialized")
            except ImportError:
                logger.error("Failed to import Adafruit PCA9685 library")
                raise
                
            logger.info("Physical motors initialized")
            
        except ImportError:
            logger.warning("RPi.GPIO not available, falling back to simulation mode")
            self.simulation_mode = True
            self.sim_logger = SimulatedLogger("motors")
    
    def set_speed(self, left_speed: int, right_speed: int):
        """
        Set the speed of both motors.
        
        Args:
            left_speed (int): Speed of left motor (-100 to 100)
            right_speed (int): Speed of right motor (-100 to 100)
        """
        # Normalize speeds to -100 to 100 range
        left_speed = max(-100, min(100, left_speed))
        right_speed = max(-100, min(100, right_speed))
        
        # Set directions based on sign
        self.directions["left"] = 1 if left_speed > 0 else (-1 if left_speed < 0 else 0)
        self.directions["right"] = 1 if right_speed > 0 else (-1 if right_speed < 0 else 0)
        
        # Set speeds (absolute values)
        self.speeds["left"] = abs(left_speed)
        self.speeds["right"] = abs(right_speed)
        
        if self.simulation_mode:
            self.sim_logger.info(
                f"Setting motor speeds - Left: {left_speed}, Right: {right_speed}"
            )
        else:
            self._set_physical_motors()
    
    def _set_physical_motors(self):
        """Set the physical motors based on current speed and direction."""
        try:
            import RPi.GPIO as GPIO
            
            # Set left motor direction
            if self.directions["left"] == 1:  # Forward
                GPIO.output(self.motor_config["left_motor"]["in1_pin"], GPIO.HIGH)
                GPIO.output(self.motor_config["left_motor"]["in2_pin"], GPIO.LOW)
            elif self.directions["left"] == -1:  # Backward
                GPIO.output(self.motor_config["left_motor"]["in1_pin"], GPIO.LOW)
                GPIO.output(self.motor_config["left_motor"]["in2_pin"], GPIO.HIGH)
            else:  # Stop
                GPIO.output(self.motor_config["left_motor"]["in1_pin"], GPIO.LOW)
                GPIO.output(self.motor_config["left_motor"]["in2_pin"], GPIO.LOW)
                
            # Set right motor direction
            if self.directions["right"] == 1:  # Forward
                GPIO.output(self.motor_config["right_motor"]["in1_pin"], GPIO.HIGH)
                GPIO.output(self.motor_config["right_motor"]["in2_pin"], GPIO.LOW)
            elif self.directions["right"] == -1:  # Backward
                GPIO.output(self.motor_config["right_motor"]["in1_pin"], GPIO.LOW)
                GPIO.output(self.motor_config["right_motor"]["in2_pin"], GPIO.HIGH)
            else:  # Stop
                GPIO.output(self.motor_config["right_motor"]["in1_pin"], GPIO.LOW)
                GPIO.output(self.motor_config["right_motor"]["in2_pin"], GPIO.LOW)
            
            # Set PWM values (convert 0-100 to 0-65535 for PCA9685)
            left_pwm = int(self.speeds["left"] * 65535 / 100)
            right_pwm = int(self.speeds["right"] * 65535 / 100)
            
            # Set PWM channels
            self.pwm.channels[self.motor_config["left_motor"]["pwm_channel"]].duty_cycle = left_pwm
            self.pwm.channels[self.motor_config["right_motor"]["pwm_channel"]].duty_cycle = right_pwm
            
            logger.debug(
                f"Set physical motors - Left: {self.directions['left']} @ {self.speeds['left']}%, "
                f"Right: {self.directions['right']} @ {self.speeds['right']}%"
            )
            
        except Exception as e:
            logger.error(f"Error setting motor speeds: {str(e)}")
    
    def move_forward(self, speed=50):
        """
        Move the robot forward.
        
        Args:
            speed (int): Speed from 0-100.
        """
        self.set_speed(speed, speed)
        
    def move_backward(self, speed=50):
        """
        Move the robot backward.
        
        Args:
            speed (int): Speed from 0-100.
        """
        self.set_speed(-speed, -speed)
        
    def turn_left(self, speed=50):
        """
        Turn the robot left in place.
        
        Args:
            speed (int): Speed from 0-100.
        """
        self.set_speed(-speed, speed)
        
    def turn_right(self, speed=50):
        """
        Turn the robot right in place.
        
        Args:
            speed (int): Speed from 0-100.
        """
        self.set_speed(speed, -speed)
        
    def stop_all(self):
        """Stop all motors."""
        self.set_speed(0, 0)
        
        if self.simulation_mode:
            self.sim_logger.info("All motors stopped")
        else:
            logger.info("All motors stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the motors.
        
        Returns:
            Dict[str, Any]: Dictionary with motor status.
        """
        return {
            "left": {
                "speed": self.speeds["left"],
                "direction": self.directions["left"]
            },
            "right": {
                "speed": self.speeds["right"],
                "direction": self.directions["right"]
            }
        } 