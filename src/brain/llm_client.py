import json
import logging
import requests
from typing import Dict, Any, Optional, List, Union, Callable, Iterator
import time

from src.config.settings import LLM_SERVER
from src.tools.robot_tools import ROBOT_TOOLS

logger = logging.getLogger(__name__)

class LLMClient:
    """Client to interact with the LLM server (Ollama with Qwen2.5:7b)."""
    
    def __init__(self, host=None, port=None, model=None):
        """
        Initialize the LLM client.
        
        Args:
            host (str, optional): LLM server host. Defaults to config value.
            port (int, optional): LLM server port. Defaults to config value.
            model (str, optional): LLM model to use. Defaults to config value.
        """
        self.host = host or LLM_SERVER["host"]
        self.port = port or LLM_SERVER["port"]
        self.model = model or LLM_SERVER["model"]
        self.base_url = f"http://{self.host}:{self.port}/api"
        self.context = []  # For maintaining conversation context
        self.tools = ROBOT_TOOLS  # Store available tools
        
        logger.info(f"LLM client initialized with model {self.model} at {self.host}:{self.port}")
        # Try to ping the Ollama server
        self._check_server_connection()
        
    def _check_server_connection(self):
        """Check if the Ollama server is reachable."""
        try:
            response = requests.get(f"http://{self.host}:{self.port}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                logger.info(f"Connected to Ollama server. Available models: {models}")
                if self.model not in models:
                    logger.warning(f"Model '{self.model}' not found in available models. You may need to pull it with 'ollama pull {self.model}'")
            else:
                logger.warning(f"Ollama server at {self.host}:{self.port} returned status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not connect to Ollama server at {self.host}:{self.port}: {str(e)}")
            logger.info("Make sure the Ollama server is running with 'ollama serve'")
        
    def _prepare_prompt(self, 
                        sensor_data: Optional[Dict[str, Any]] = None,
                        camera_data: Optional[Dict[str, Any]] = None,
                        custom_prompt: Optional[str] = None) -> str:
        """
        Prepare a prompt for the LLM based on sensor data and optional custom prompt.
        
        Args:
            sensor_data (Dict, optional): Dictionary of sensor readings.
            camera_data (Dict, optional): Dictionary with camera frame info.
            custom_prompt (str, optional): Custom instructions to override defaults.
            
        Returns:
            str: The formatted prompt for the LLM.
        """
        # Start with the system prompt
        system_prompt = """
        You are Meebo, an AI-powered robot capable of interacting with the environment.
        Your responses should be concise and focused on helping your robot body navigate and interact.
        
        You have the following capabilities:
        1. Process sensor data to understand the environment
        2. Make decisions about movement and actions
        3. Respond to voice commands
        4. Provide status updates
        
        Available tools:
        """
        
        # Add available tools to the prompt
        for tool in self.tools:
            if isinstance(tool, dict) and "function" in tool:
                func = tool["function"]
                system_prompt += f"\n{func['name']}: {func['description']}"
                if "parameters" in func and "properties" in func["parameters"]:
                    params = func["parameters"]["properties"]
                    if params:
                        system_prompt += "\nParameters:"
                        for param_name, param_info in params.items():
                            param_desc = param_info.get("description", "")
                            param_type = param_info.get("type", "unknown")
                            system_prompt += f"\n  - {param_name} ({param_type}): {param_desc}"
        
        system_prompt += """
        
        IMPORTANT: Your response should follow this format:
        
        ACTIONS:
        tool_name(param1=value1, param2=value2)
        tool_name2(param1=value1)
        
        THOUGHTS:
        Your reasoning about the current situation and what actions to take...
        
        The ACTIONS section should list each tool call on a new line in the format:
        tool_name(param1=value1, param2=value2)
        
        Always choose the most appropriate tool for the situation based on the sensor readings.
        """
        
        # If custom prompt is provided, use it instead
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Format sensor data
            sensor_section = ""
            if sensor_data:
                sensor_section = "Current sensor readings:\n" + json.dumps(sensor_data, indent=2)
            
            # Format camera data (simplified)
            camera_section = ""
            if camera_data:
                camera_info = {
                    "resolution": camera_data.get("resolution", "unknown"),
                    "has_motion": camera_data.get("has_motion", False),
                    "objects_detected": camera_data.get("objects_detected", [])
                }
                camera_section = "Current camera data:\n" + json.dumps(camera_info, indent=2)
            
            # Combine everything
            prompt = f"{system_prompt}\n\n{sensor_section}\n\n{camera_section}\n\nWhat should I do next?"
        
        return prompt
    
    def _prepare_tools(self, tools: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Prepare tool definitions for the LLM.
        
        Args:
            tools (List[Dict], optional): List of tool definitions to provide to the LLM.
            
        Returns:
            List[Dict]: The formatted tools list or an empty list if none provided.
        """
        if not tools:
            return []
            
        # Ensure each tool has the required structure
        valid_tools = []
        for tool in tools:
            # Check if tool has minimum required structure
            if not isinstance(tool, dict) or "type" not in tool or "function" not in tool:
                # Basic structure for function tools
                if "name" in tool and "description" in tool:
                    # Convert simple format to full format
                    valid_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool.get("parameters", {
                                "type": "object",
                                "properties": {}
                            })
                        }
                    })
                else:
                    logger.warning(f"Skipping invalid tool definition: {tool}")
            else:
                valid_tools.append(tool)
                
        return valid_tools
        
    def process_streaming(self, 
                         sensor_data: Optional[Dict[str, Any]] = None,
                         camera_data: Optional[Dict[str, Any]] = None, 
                         custom_prompt: Optional[str] = None,
                         tools: Optional[List[Dict[str, Any]]] = None,
                         callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Iterator[Dict[str, Any]]:
        """
        Process data through the LLM with streaming responses.
        
        Args:
            sensor_data (Dict, optional): Dictionary of sensor readings.
            camera_data (Dict, optional): Dictionary with camera frame info.
            custom_prompt (str, optional): Custom instructions to override defaults.
            tools (List[Dict], optional): List of tool definitions to provide to the LLM.
            callback (Callable, optional): Function to call for each chunk of the response.
            
        Yields:
            Dict: Response chunks from the LLM with thoughts and actions.
        """
        prompt = self._prepare_prompt(sensor_data, camera_data, custom_prompt)
        prepared_tools = self._prepare_tools(tools or self.tools)  # Use instance tools if none provided
        self.tools = prepared_tools  # Store the tools list for validation
        
        # Buffer for accumulating the complete response
        complete_response = ""
        response_count = 0
        last_actions = []  # Track last parsed actions to detect changes
        
        try:
            # Prepare the request to Ollama
            request_payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "context": self.context
            }
            
            # Add tools if provided
            if prepared_tools:
                request_payload["tools"] = prepared_tools
            
            # Log request details
            logger.debug(f"Sending streaming request to {self.base_url}/generate")
            logger.debug(f"Using model: {self.model}")
            if sensor_data:
                logger.debug(f"Sensor data included: {len(sensor_data.keys())} keys")
            if camera_data:
                logger.debug(f"Camera data included: {len(camera_data.get('objects_detected', []))} objects detected")
            if len(self.context) > 0:
                logger.debug(f"Using conversation context with {len(self.context)} tokens")
            if prepared_tools:
                logger.debug(f"Using {len(prepared_tools)} tools")
                logger.debug(f"Available tools: {[tool['function']['name'] for tool in prepared_tools]}")
            
            # Make the API call with streaming
            start_time = time.time()
            with requests.post(
                f"{self.base_url}/generate",
                json=request_payload,
                timeout=30,
                stream=True
            ) as response:
                if response.status_code == 200:
                    # Process each chunk of the streaming response
                    for line in response.iter_lines():
                        if line:
                            # Decode the line and parse the JSON
                            line_str = line.decode('utf-8')
                            try:
                                chunk = json.loads(line_str)
                                response_count += 1
                                
                                # Update the context if provided in the chunk
                                if "context" in chunk:
                                    self.context = chunk["context"]
                                
                                # Append to the complete response
                                if "response" in chunk:
                                    complete_response += chunk["response"]
                                
                                # Try to parse the accumulated response
                                try:
                                    parsed_chunk = self._parse_llm_response(complete_response)
                                    
                                    # Check if actions have changed
                                    if parsed_chunk["actions"] != last_actions:
                                        last_actions = parsed_chunk["actions"]
                                        # Log new actions
                                        for action in parsed_chunk["actions"]:
                                            logger.info(f"New action detected: {action['tool']} with params {action['params']}")
                                    
                                    # Create a chunk result
                                    chunk_result = {
                                        "thoughts": parsed_chunk["thoughts"],
                                        "actions": parsed_chunk["actions"],
                                        "complete": chunk.get("done", False)
                                    }
                                    
                                    # Call the callback if provided
                                    if callback:
                                        callback(chunk_result)
                                    
                                    # Yield the chunk result
                                    yield chunk_result
                                    
                                    # If done, break the loop
                                    if chunk.get("done", False):
                                        break
                                except Exception as e:
                                    # If we can't parse yet, just yield the raw text
                                    chunk_result = {
                                        "thoughts": complete_response,
                                        "actions": [],
                                        "complete": chunk.get("done", False)
                                    }
                                    if callback:
                                        callback(chunk_result)
                                    yield chunk_result
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON from streaming response: {line_str}")
                else:
                    error_msg = f"Error from LLM API: {response.status_code}"
                    logger.error(error_msg)
                    yield {
                        "thoughts": f"Error: {error_msg}",
                        "actions": [],
                        "complete": True
                    }
                    
            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"LLM streaming response completed in {elapsed_time:.2f} seconds ({response_count} chunks)")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            yield {
                "thoughts": f"Error: {error_msg}",
                "actions": [],
                "complete": True
            }
        except Exception as e:
            error_msg = f"Error processing LLM response: {str(e)}"
            logger.error(error_msg)
            yield {
                "thoughts": f"Error: {error_msg}",
                "actions": [],
                "complete": True
            }
        
    def process(self, 
               sensor_data: Optional[Dict[str, Any]] = None,
               camera_data: Optional[Dict[str, Any]] = None, 
               custom_prompt: Optional[str] = None,
               tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process data through the LLM.
        
        Args:
            sensor_data (Dict, optional): Dictionary of sensor readings.
            camera_data (Dict, optional): Dictionary with camera frame info.
            custom_prompt (str, optional): Custom instructions to override defaults.
            tools (List[Dict], optional): List of tool definitions to provide to the LLM.
            
        Returns:
            Dict: Response from the LLM with thoughts and actions.
        """
        prompt = self._prepare_prompt(sensor_data, camera_data, custom_prompt)
        prepared_tools = self._prepare_tools(tools or self.tools)  # Use instance tools if none provided
        self.tools = prepared_tools  # Store the tools list for validation
        
        try:
            # Prepare the request to Ollama
            request_payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "context": self.context
            }
            
            # Add tools if provided
            if prepared_tools:
                request_payload["tools"] = prepared_tools
            
            # Log request details (without verbose prompt and context)
            logger.debug(f"Sending request to {self.base_url}/generate")
            logger.debug(f"Using model: {self.model}")
            if sensor_data:
                logger.debug(f"Sensor data included: {len(sensor_data.keys())} keys")
            if camera_data:
                logger.debug(f"Camera data included: {len(camera_data.get('objects_detected', []))} objects detected")
            if len(self.context) > 0:
                logger.debug(f"Using conversation context with {len(self.context)} tokens")
            if prepared_tools:
                logger.debug(f"Using {len(prepared_tools)} tools")
                logger.debug(f"Available tools: {[tool['function']['name'] for tool in prepared_tools]}")
            
            # Make the API call
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/generate",
                json=request_payload,
                timeout=30
            )
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Check for success
            if response.status_code == 200:
                result = response.json()
                old_context_size = len(self.context)
                self.context = result.get("context", [])
                new_context_size = len(self.context)
                
                logger.info(f"LLM response received in {elapsed_time:.2f} seconds")
                logger.debug(f"Context tokens: {old_context_size} → {new_context_size}")
                
                if "response" in result:
                    # Parse the response into our structured format
                    parsed_response = self._parse_llm_response(result["response"])
                    
                    # Log the thoughts and actions
                    logger.info(f"LLM thoughts: {parsed_response['thoughts']}")
                    if parsed_response["actions"]:
                        logger.info(f"LLM actions: {len(parsed_response['actions'])} actions")
                        for action in parsed_response["actions"]:
                            logger.info(f"Action: {action['tool']} with params {action['params']}")
                    
                    return parsed_response
                else:
                    logger.error("No response field in LLM result")
                    return {
                        "thoughts": "Error: No response received from LLM",
                        "actions": []
                    }
            else:
                logger.error(f"Error from LLM API: {response.status_code} - {response.text}")
                return {
                    "thoughts": f"Error: API returned status code {response.status_code}",
                    "actions": []
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {
                "thoughts": f"Error: Request failed - {str(e)}",
                "actions": []
            }
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            return {
                "thoughts": f"Error: Processing error - {str(e)}",
                "actions": []
            }
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the LLM response text to extract actions and thoughts.
        
        Args:
            response_text (str): The raw text response from the LLM.
            
        Returns:
            Dict: Parsed response with thoughts and actions.
        """
        try:
            # Split response into actions and thoughts sections
            sections = response_text.split("THOUGHTS:", 1)
            actions_text = sections[0].strip()
            thoughts_text = sections[1].strip() if len(sections) > 1 else ""
            
            # Extract actions from the ACTIONS section
            actions = []
            if "ACTIONS:" in actions_text:
                actions_text = actions_text.split("ACTIONS:", 1)[1].strip()
                for line in actions_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Parse tool call in format: tool_name(param1=value1, param2=value2)
                    if "(" in line and line.endswith(")"):
                        tool_name = line[:line.find("(")].strip()
                        params_str = line[line.find("(")+1:line.rfind(")")].strip()
                        
                        # Validate tool name against available tools
                        if not self._is_valid_tool(tool_name):
                            logger.warning(f"Invalid tool name detected: {tool_name}")
                            continue
                        
                        # Parse parameters
                        params = {}
                        if params_str:
                            for param in params_str.split(","):
                                param = param.strip()
                                if "=" in param:
                                    key, value = param.split("=", 1)
                                    # Try to convert value to appropriate type
                                    try:
                                        value = json.loads(value)
                                    except json.JSONDecodeError:
                                        # Keep as string if not valid JSON
                                        pass
                                    params[key.strip()] = value
                        
                        actions.append({
                            "tool": tool_name,
                            "params": params
                        })
            
            return {
                "thoughts": thoughts_text,
                "actions": actions
            }
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {
                "thoughts": "Error: Failed to parse response",
                "actions": []
            }
    
    def _is_valid_tool(self, tool_name: str) -> bool:
        """
        Check if a tool name is valid by checking against available tools.
        
        Args:
            tool_name (str): The name of the tool to validate.
            
        Returns:
            bool: True if the tool is valid, False otherwise.
        """
        # Get the list of available tool names
        available_tools = []
        for tool in self._prepare_tools(self.tools):
            if isinstance(tool, dict):
                if "function" in tool:
                    available_tools.append(tool["function"]["name"])
                elif "name" in tool:
                    available_tools.append(tool["name"])
        
        # Check if the tool name is in the list
        is_valid = tool_name in available_tools
        if not is_valid:
            logger.warning(f"Tool '{tool_name}' not found in available tools: {available_tools}")
        return is_valid
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Execute a registered tool by name with the provided parameters.
        
        Args:
            tool_name (str): The name of the tool to execute.
            params (Dict): Parameters to pass to the tool.
            
        Returns:
            Any: The result of the tool execution.
        """
        # This method would be implemented to handle tool execution.
        # For now, just log the tool call and return a placeholder response.
        logger.info(f"Tool call: {tool_name} with params {params}")
        return {
            "result": f"Executed {tool_name}",
            "params_received": params
        } 