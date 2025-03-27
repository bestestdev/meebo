import logging
import time
import random
import numpy as np
from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path

from src.config.settings import CAMERA, IS_RASPBERRY_PI
from src.utils.logger import SimulatedLogger

logger = logging.getLogger(__name__)

class CameraManager:
    """
    Manager for the robot's camera. Handles both real and simulated camera.
    Provides a unified interface for capturing and processing images.
    """
    
    def __init__(self, simulation_mode=False):
        """
        Initialize the camera manager.
        
        Args:
            simulation_mode (bool): Whether to use a simulated camera.
        """
        self.simulation_mode = simulation_mode
        self.camera_config = CAMERA
        self.camera = None
        self.frame_count = 0
        self.last_frame = None
        self.last_processed_frame = None
        
        # Track detected objects (for simulation)
        self.simulated_objects = []
        
        if simulation_mode:
            self.sim_logger = SimulatedLogger("camera")
            self.sim_logger.info("Initializing simulated camera")
            self._init_simulated_camera()
        else:
            logger.info("Initializing physical camera")
            self._init_physical_camera()
            
        logger.info(f"Camera manager initialized (simulation: {simulation_mode})")
    
    def _init_physical_camera(self):
        """Initialize the physical camera."""
        if not IS_RASPBERRY_PI:
            logger.warning("Not running on Raspberry Pi. Falling back to simulation mode.")
            self.simulation_mode = True
            self.sim_logger = SimulatedLogger("camera")
            self._init_simulated_camera()
            return
            
        try:
            # Try to import picamera2 (for Raspberry Pi)
            from picamera2 import Picamera2
            
            # Initialize the camera
            self.camera = Picamera2()
            
            # Configure the camera
            config = self.camera.create_still_configuration(
                main={"size": self.camera_config["resolution"]},
                lores={"size": (320, 240)},
                display="lores"
            )
            self.camera.configure(config)
            
            # Start the camera
            self.camera.start()
            
            logger.info(f"Physical camera initialized with resolution {self.camera_config['resolution']}")
            
        except ImportError:
            logger.warning("PiCamera2 not available. Trying OpenCV camera...")
            try:
                import cv2
                
                # Initialize the camera with OpenCV
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_config["resolution"][0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_config["resolution"][1])
                self.camera.set(cv2.CAP_PROP_FPS, self.camera_config["framerate"])
                
                # Check if camera opened successfully
                if not self.camera.isOpened():
                    raise Exception("Failed to open camera with OpenCV")
                
                logger.info(f"OpenCV camera initialized with resolution {self.camera_config['resolution']}")
                
            except Exception as e:
                logger.error(f"Failed to initialize camera: {str(e)}")
                logger.warning("Falling back to simulation mode")
                self.simulation_mode = True
                self.sim_logger = SimulatedLogger("camera")
                self._init_simulated_camera()
                
    def _init_simulated_camera(self):
        """Initialize a simulated camera."""
        try:
            import cv2
            import numpy as np
            
            # Create a black image for simulation
            self.simulated_frame = np.zeros(
                (self.camera_config["resolution"][1], self.camera_config["resolution"][0], 3),
                dtype=np.uint8
            )
            
            # Add some visual elements to the simulated frame
            cv2.putText(
                self.simulated_frame,
                "SIMULATED CAMERA",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            self.sim_logger.info(f"Simulated camera initialized with resolution {self.camera_config['resolution']}")
            
        except ImportError:
            self.sim_logger.warning("OpenCV not available for simulation, using minimal simulation")
            # Just use a simple placeholder for simulation without OpenCV
            self.simulated_frame = {
                "width": self.camera_config["resolution"][0],
                "height": self.camera_config["resolution"][1],
                "channels": 3,
                "simulated": True
            }
    
    def get_frame(self) -> Dict[str, Any]:
        """
        Capture a frame from the camera.
        
        Returns:
            Dict[str, Any]: Dictionary with frame data and metadata.
        """
        self.frame_count += 1
        timestamp = time.time()
        
        if self.simulation_mode:
            return self._get_simulated_frame(timestamp)
        else:
            return self._get_physical_frame(timestamp)
    
    def _get_physical_frame(self, timestamp: float) -> Dict[str, Any]:
        """
        Capture a frame from the physical camera.
        
        Args:
            timestamp (float): Timestamp when the frame was requested.
            
        Returns:
            Dict[str, Any]: Dictionary with frame data and metadata.
        """
        try:
            # Check if we're using PiCamera2 or OpenCV
            if hasattr(self.camera, 'capture_array'):  # PiCamera2
                # Capture frame using PiCamera2
                frame = self.camera.capture_array()
                self.last_frame = frame
                
                # Basic frame info
                frame_info = {
                    "timestamp": timestamp,
                    "frame_count": self.frame_count,
                    "resolution": (frame.shape[1], frame.shape[0]),
                    "has_frame": True,
                    "frame": frame
                }
                
            else:  # OpenCV
                # Capture frame using OpenCV
                ret, frame = self.camera.read()
                
                if ret:
                    self.last_frame = frame
                    
                    # Basic frame info
                    frame_info = {
                        "timestamp": timestamp,
                        "frame_count": self.frame_count,
                        "resolution": (frame.shape[1], frame.shape[0]),
                        "has_frame": True,
                        "frame": frame
                    }
                else:
                    logger.error("Failed to capture frame from camera")
                    frame_info = {
                        "timestamp": timestamp,
                        "frame_count": self.frame_count,
                        "resolution": self.camera_config["resolution"],
                        "has_frame": False,
                        "error": "Failed to capture frame"
                    }
            
            # Process the frame for additional data
            if "frame" in frame_info and frame_info["has_frame"]:
                # Here we would normally do more image processing
                # For now, just add placeholder data
                frame_info["has_motion"] = False
                frame_info["objects_detected"] = []
                
            return frame_info
            
        except Exception as e:
            logger.error(f"Error capturing frame: {str(e)}")
            return {
                "timestamp": timestamp,
                "frame_count": self.frame_count,
                "resolution": self.camera_config["resolution"],
                "has_frame": False,
                "error": str(e)
            }
    
    def _get_simulated_frame(self, timestamp: float) -> Dict[str, Any]:
        """
        Generate a simulated frame.
        
        Args:
            timestamp (float): Timestamp when the frame was requested.
            
        Returns:
            Dict[str, Any]: Dictionary with simulated frame data and metadata.
        """
        try:
            import cv2
            import numpy as np
            
            # Create a copy of the base simulated frame
            frame = self.simulated_frame.copy()
            
            # Add some dynamic content to the frame
            # Add a moving dot to simulate motion
            dot_x = int(self.camera_config["resolution"][0] / 2 + 
                       (self.camera_config["resolution"][0] / 4) * 
                       np.sin(self.frame_count / 30))
            dot_y = int(self.camera_config["resolution"][1] / 2 + 
                       (self.camera_config["resolution"][1] / 4) * 
                       np.cos(self.frame_count / 20))
            
            cv2.circle(frame, (dot_x, dot_y), 20, (0, 0, 255), -1)
            
            # Add frame count
            cv2.putText(
                frame,
                f"Frame: {self.frame_count}",
                (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )
            
            # Add timestamp
            cv2.putText(
                frame,
                f"Time: {timestamp:.2f}",
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )
            
            # Periodically add 'objects' to detect
            if self.frame_count % 100 == 0:
                # Generate a random object at a random position
                objects = ["person", "wall", "chair", "table", "door"]
                obj = random.choice(objects)
                obj_x = random.randint(0, frame.shape[1] - 1)
                obj_y = random.randint(0, frame.shape[0] - 1)
                
                self.simulated_objects.append({
                    "type": obj,
                    "position": (obj_x, obj_y),
                    "confidence": random.uniform(0.7, 0.99),
                    "lifetime": random.randint(50, 150)  # How many frames it will exist
                })
                
            # Update and draw existing simulated objects
            active_objects = []
            for obj in self.simulated_objects:
                obj["lifetime"] -= 1
                if obj["lifetime"] > 0:
                    # Draw the object
                    cv2.putText(
                        frame,
                        f"{obj['type']} ({obj['confidence']:.2f})",
                        obj["position"],
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 0),
                        1
                    )
                    cv2.rectangle(
                        frame,
                        (obj["position"][0] - 20, obj["position"][1] - 20),
                        (obj["position"][0] + 20, obj["position"][1] + 20),
                        (255, 255, 0),
                        2
                    )
                    active_objects.append(obj)
            
            self.simulated_objects = active_objects
            
            # Store the frame
            self.last_frame = frame
            
            # Return frame info
            frame_info = {
                "timestamp": timestamp,
                "frame_count": self.frame_count,
                "resolution": (frame.shape[1], frame.shape[0]),
                "has_frame": True,
                "frame": frame,
                "has_motion": len(self.simulated_objects) > 0,
                "objects_detected": [
                    {
                        "type": obj["type"],
                        "confidence": obj["confidence"],
                        "position": obj["position"]
                    } for obj in self.simulated_objects
                ]
            }
            
            self.sim_logger.debug(f"Generated simulated frame #{self.frame_count}")
            return frame_info
            
        except ImportError:
            # Fallback if OpenCV is not available
            self.sim_logger.warning("OpenCV not available for simulation, using minimal frame data")
            
            # Return minimal frame info
            return {
                "timestamp": timestamp,
                "frame_count": self.frame_count,
                "resolution": self.camera_config["resolution"],
                "has_frame": True,
                "has_motion": random.random() > 0.7,
                "objects_detected": [
                    {
                        "type": random.choice(["person", "wall", "chair"]),
                        "confidence": random.uniform(0.7, 0.99),
                        "position": (
                            random.randint(0, self.camera_config["resolution"][0]),
                            random.randint(0, self.camera_config["resolution"][1])
                        )
                    } for _ in range(random.randint(0, 3))
                ] if random.random() > 0.5 else []
            }
    
    def detect_objects(self, frame=None) -> List[Dict[str, Any]]:
        """
        Detect objects in the given frame or the last captured frame.
        
        Args:
            frame: Optional frame to process. If None, uses the last captured frame.
            
        Returns:
            List[Dict[str, Any]]: List of detected objects with type, position, and confidence.
        """
        if frame is None:
            frame = self.last_frame
            
        if frame is None:
            logger.warning("No frame available for object detection")
            return []
            
        if self.simulation_mode:
            # For simulation, return the objects we already generated
            if hasattr(self, 'simulated_objects'):
                return [
                    {
                        "type": obj["type"],
                        "confidence": obj["confidence"],
                        "position": obj["position"]
                    } for obj in self.simulated_objects
                ]
            else:
                return []
        else:
            # In real mode, we would use a real object detection model
            # But for this stub, just return empty list
            logger.info("Object detection not implemented for real camera yet")
            return []
    
    def release(self):
        """Release camera resources."""
        if not self.simulation_mode and self.camera is not None:
            try:
                # Check if we're using PiCamera2 or OpenCV
                if hasattr(self.camera, 'stop'):  # PiCamera2
                    self.camera.stop()
                else:  # OpenCV
                    self.camera.release()
                    
                logger.info("Camera resources released")
            except Exception as e:
                logger.error(f"Error releasing camera: {str(e)}")
        elif self.simulation_mode:
            self.sim_logger.info("Simulated camera resources released") 