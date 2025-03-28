#!/usr/bin/env python3
"""
Meebo Robot Control System - Main Entry Point
"""
import argparse
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
import json
import os
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import DEV_MODE, IS_RASPBERRY_PI
from src.utils.logger import setup_logger
from src.brain.llm_client import LLMClient
from src.sensors.sensor_manager import SensorManager
from src.actuators.motor_controller import MotorController
from src.audio.audio_manager import AudioManager
from src.vision.camera_manager import CameraManager
from src.tools.robot_tools import ROBOT_TOOLS

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Meebo Robot Control System")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    parser.add_argument("--log-level", type=str, default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode with voice commands")
    return parser.parse_args()

class MeeboRobot:
    """Main robot control class that coordinates all subsystems."""
    
    def __init__(self, dev_mode=False, interactive=False):
        """Initialize the robot subsystems."""
        self.dev_mode = dev_mode or DEV_MODE
        self.interactive = interactive
        logger.info(f"Initializing Meebo Robot (Dev Mode: {self.dev_mode}, Interactive: {self.interactive})")
        
        # Initialize subsystems
        self.brain = LLMClient()
        self.sensors = SensorManager(simulation_mode=self.dev_mode)
        self.motors = MotorController(simulation_mode=self.dev_mode)
        self.audio = AudioManager()
        self.camera = CameraManager(simulation_mode=self.dev_mode)
        
        # Runtime state
        self.running = False
        self.last_voice_command = None
        self.last_error = None
        self.loop_count = 0
        self.use_streaming = True  # Enable streaming by default
        
        # Startup message
        self.audio.say("Meebo robot initialized and ready.", wait=False)
        logger.info("Meebo Robot initialized successfully")
        
    def start(self):
        """Start the robot's main control loop."""
        self.running = True
        logger.info("Starting Meebo Robot control loop")
        
        try:
            # Main control loop
            while self.running:
                self.loop_count += 1
                
                # Get sensor data
                sensor_data = self.sensors.get_all_readings()
                camera_data = self.camera.get_frame()
                
                # Check for voice commands in interactive mode
                if self.interactive and self.loop_count % 10 == 0:  # Check every ~1 second
                    voice_command = self.audio.listen_for_command(timeout=3.0)
                    if voice_command:
                        self.last_voice_command = voice_command
                        logger.info(f"Voice command received: {voice_command}")
                        
                        # Process voice command with LLM
                        custom_prompt = f"""
                        You are Meebo, an AI-powered robot. You just received a voice command: "{voice_command}"
                        
                        Current sensor readings:
                        {sensor_data}
                        
                        Respond with appropriate actions to take based on this voice command.
                        """
                        
                        if self.use_streaming:
                            self._process_streaming(custom_prompt=custom_prompt, tools=ROBOT_TOOLS)
                        else:
                            llm_response = self.brain.process(custom_prompt=custom_prompt, tools=ROBOT_TOOLS)
                            self._handle_llm_response(llm_response)
                    else:
                        # Regular environmental processing
                        if self.use_streaming:
                            self._process_streaming(sensor_data=sensor_data, camera_data=camera_data, tools=ROBOT_TOOLS)
                        else:
                            llm_response = self.brain.process(
                                sensor_data=sensor_data,
                                camera_data=camera_data,
                                tools=ROBOT_TOOLS
                            )
                            self._handle_llm_response(llm_response)
                else:
                    # Regular environmental processing
                    if self.use_streaming:
                        self._process_streaming(sensor_data=sensor_data, camera_data=camera_data, tools=ROBOT_TOOLS)
                    else:
                        llm_response = self.brain.process(
                            sensor_data=sensor_data,
                            camera_data=camera_data,
                            tools=ROBOT_TOOLS
                        )
                        self._handle_llm_response(llm_response)
                
                # Short sleep to prevent CPU hogging
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def _process_streaming(self, sensor_data=None, camera_data=None, custom_prompt=None, tools=None):
        """
        Process data through the LLM with streaming responses.
        
        Args:
            sensor_data: Sensor readings
            camera_data: Camera frame data
            custom_prompt: Custom prompt override
            tools: List of tools to provide to the LLM
        """
        # For real-time feedback, we'll use the streaming callback to process partial results
        accumulated_response = {}
        
        def streaming_callback(chunk):
            """Handle each chunk of the streaming response."""
            nonlocal accumulated_response
            
            # Save chunk if it's the final one
            if chunk.get("complete", False):
                accumulated_response = chunk
            
            # Check for tool calls in the chunk
            if "raw_chunk" in chunk and "tool_calls" in chunk["raw_chunk"]:
                tool_calls = chunk["raw_chunk"]["tool_calls"]
                if tool_calls:
                    # Process tool calls as they come in streaming response
                    logger.info(f"Found {len(tool_calls)} tool call(s) in streaming chunk")
                    self._handle_tool_calls(tool_calls)
                    # Log that we're executing tool calls immediately from streaming
                    logger.debug("Executing tool calls from streaming chunk")
            
            # Log last part of accumulated text for debugging
            if "text" in chunk and chunk.get("text"):
                text = chunk.get("text", "")
                if len(text) > 0 and text.strip() != "":
                    # Parse text for Python-style function calls (e.g., call_move_forward(0.5))
                    if "call_" in text:
                        # Extract any function calls from the text
                        tool_calls = self._parse_function_calls_from_text(text)
                        if tool_calls:
                            logger.info(f"Parsed {len(tool_calls)} function call(s) from text")
                            self._handle_tool_calls(tool_calls)
                    
                    last_part = text[-40:] if len(text) > 40 else text
                    logger.debug(f"Accumulated text ending with: {last_part}")
        
        # Process streaming with callback
        for _ in self.brain.process_streaming(
            sensor_data=sensor_data,
            camera_data=camera_data,
            custom_prompt=custom_prompt,
            tools=tools,
            callback=streaming_callback
        ):
            # Chunks are handled by the callback
            pass
        
        # Check if we need to handle tool calls from the complete response
        if accumulated_response and "tool_calls" in accumulated_response:
            self._handle_tool_calls(accumulated_response["tool_calls"])
    
    def _parse_function_calls_from_text(self, text):
        """
        Parse Python-style function calls from text output.
        
        Args:
            text (str): The text to parse for function calls
            
        Returns:
            list: A list of parsed tool calls
        """
        import re
        
        # Initialize results
        tool_calls = []
        
        # Find all instances of function_name patterns
        # Pattern matches: move_forward(args), turn_left(args), etc.
        pattern = r'([a-z_]+)\(([0-9\.]+)\)'
        matches = re.findall(pattern, text)
        
        # Convert each match to a tool call
        for match in matches:
            function_name = match[0]  # The function name
            arg_value = float(match[1])  # Convert argument to float
            
            # Convert to integer if it's a whole number
            if arg_value.is_integer():
                arg_value = int(arg_value)
            
            # Create the tool call object
            tool_call = {
                "id": f"call_{len(tool_calls)}",
                "function": {
                    "name": function_name,
                    "arguments": json.dumps({"speed": arg_value})
                }
            }
            
            # Add to results
            tool_calls.append(tool_call)
            logger.info(f"Parsed function call: {function_name}({arg_value})")
        
        return tool_calls
    
    def _handle_llm_response(self, llm_response):
        """
        Handle the LLM response, focusing on tool calls.
        
        Args:
            llm_response (dict): Response from the LLM
        """
        if not llm_response:
            return
            
        if "error" in llm_response:
            self.last_error = llm_response["error"]
            logger.error(f"LLM error: {self.last_error}")
            return
            
        # Process tool calls
        if "tool_calls" in llm_response:
            self._handle_tool_calls(llm_response["tool_calls"])
    
    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]):
        """
        Handle tool calls from the LLM.
        
        Args:
            tool_calls (List[Dict]): List of tool calls from the LLM
        """
        # Log the incoming tool calls
        logger.info(f"Received {len(tool_calls)} tool calls from LLM")
        for i, tool_call in enumerate(tool_calls):
            if "function" in tool_call:
                function_name = tool_call["function"]["name"]
                function_args = tool_call["function"].get("arguments", "{}")
                logger.info(f"Tool call #{i+1}: {function_name} with args: {function_args}")
        
        # Execute each tool call
        results = []
        for tool_call in tool_calls:
            if "function" in tool_call:
                function_name = tool_call["function"]["name"]
                function_args = {}
                
                # Parse arguments if provided
                if "arguments" in tool_call["function"]:
                    try:
                        function_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse arguments: {tool_call['function']['arguments']}")
                
                # Execute the tool function
                result = self._execute_tool(function_name, function_args)
                
                # Add to results
                results.append({
                    "tool_call_id": tool_call.get("id", "unknown"),
                    "function_name": function_name,
                    "result": result
                })
        
        # Log the results
        if results:
            logger.info(f"Executed {len(results)} tool calls")
            
            # Here we could send the tool results back to the LLM for further processing
            # This would be done by creating a new custom prompt with the tool results
    
    def _execute_tool(self, function_name: str, params: Dict[str, Any]) -> Any:
        """
        Execute a tool function.
        
        Args:
            function_name (str): Name of the function to execute
            params (Dict): Parameters for the function
            
        Returns:
            Any: Result of the function
        """
        logger.info(f"Executing tool: {function_name} with params {params}")
        
        try:
            # Information retrieval tools
            if function_name == "get_motor_status":
                return self.motors.get_status()
                
            elif function_name == "check_battery":
                # Simulate battery check
                return {"level": 75, "status": "charging" if self.loop_count % 2 == 0 else "discharging"}
            
            # Movement tools
            elif function_name == "move_forward":
                speed = int(params.get("speed", 50))
                self.motors.move_forward(speed)
                logger.info(f"Moving forward at speed {speed}")
                return {"success": True, "action": "move_forward", "speed": speed}
                
            elif function_name == "move_backward":
                speed = int(params.get("speed", 50))
                self.motors.move_backward(speed)
                logger.info(f"Moving backward at speed {speed}")
                return {"success": True, "action": "move_backward", "speed": speed}
                
            elif function_name == "turn_left":
                speed = int(params.get("speed", 50))
                self.motors.turn_left(speed)
                logger.info(f"Turning left at speed {speed}")
                return {"success": True, "action": "turn_left", "speed": speed}
                
            elif function_name == "turn_right":
                speed = int(params.get("speed", 50))
                self.motors.turn_right(speed)
                logger.info(f"Turning right at speed {speed}")
                return {"success": True, "action": "turn_right", "speed": speed}
                
            elif function_name == "stop":
                self.motors.stop_all()
                logger.info("Stopping all motors")
                return {"success": True, "action": "stop"}
            
            # Audio and sensor tools
            elif function_name == "speak":
                text = params.get("text", "")
                wait = params.get("wait", False)
                
                if text:
                    self.audio.say(text, wait=wait)
                    logger.info(f"Speaking: {text}")
                    return {"success": True, "action": "speak", "text": text}
                else:
                    logger.warning("Speak action with empty text")
                    return {"success": False, "error": "Empty text provided"}
                    
            elif function_name == "listen":
                timeout = float(params.get("timeout", 5.0))
                logger.info(f"Listening for command with timeout {timeout}s")
                
                voice_command = self.audio.listen_for_command(timeout=timeout)
                if voice_command:
                    self.last_voice_command = voice_command
                    logger.info(f"Voice command received: {voice_command}")
                    return {"success": True, "action": "listen", "command": voice_command}
                else:
                    return {"success": True, "action": "listen", "command": None}
                    
            elif function_name == "capture_image":
                logger.info("Capturing image")
                # In the future, we could save the current camera frame to a file
                # For now, just return info about the current frame
                camera_info = {
                    "resolution": self.camera.get_frame().get("resolution", "unknown"),
                    "has_frame": True,
                    "timestamp": time.time()
                }
                return {"success": True, "action": "capture_image", "frame_info": camera_info}
                
            else:
                logger.warning(f"Unknown tool function: {function_name}")
                return {"error": f"Unknown tool function: {function_name}"}
                
        except Exception as e:
            error_message = f"Error executing tool {function_name}: {str(e)}"
            logger.error(error_message)
            return {"success": False, "error": error_message}
    
    def stop(self):
        """Stop the robot and clean up resources."""
        self.running = False
        logger.info("Stopping Meebo Robot")
        
        # Clean up resources
        self.sensors.cleanup()
        self.motors.stop_all()
        self.camera.release()
        self.audio.cleanup()
        
        # Goodbye message
        logger.info("Meebo Robot stopped successfully")

def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"meebo_{timestamp}.log"
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Logging initialized at level {level}")
    logging.info(f"Log file: {log_file}")

def main():
    """Main entry point for the Meebo robot."""
    parser = argparse.ArgumentParser(description='Run the Meebo robot')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--log-level', default='INFO', help='Set logging level')
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(log_level)
    
    # Check if running on Raspberry Pi
    is_pi = os.uname().machine.startswith('arm')
    if not is_pi:
        logging.info("Running on non-Raspberry Pi system")
    
    # Initialize robot
    logging.info(f"Initializing Meebo Robot (Dev Mode: {args.dev}, Interactive: {args.interactive})")
    
    try:
        # Initialize components
        llm_client = LLMClient()
        sensors = SensorManager(simulation_mode=args.dev)
        camera = CameraManager(simulation_mode=args.dev)
        
        logging.info("Meebo Robot initialized successfully")
        logging.info("Starting Meebo Robot control loop")
        
        # Main control loop
        while True:
            # Get real sensor data
            sensor_data = sensors.get_all_readings()
            camera_data = camera.get_frame()
            
            # Process through LLM
            response = llm_client.process(
                sensor_data=sensor_data,
                camera_data=camera_data,
                tools=ROBOT_TOOLS
            )
            
            # Execute actions
            for action in response["actions"]:
                result = llm_client.execute_tool(action["tool"], action["params"])
                logging.info(f"Action result: {result}")
            
            # Small delay to prevent CPU spinning
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
        logging.info("Stopping Meebo Robot")
    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")
        raise
    finally:
        logging.info("Meebo Robot stopped successfully")

if __name__ == "__main__":
    main()
