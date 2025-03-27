import json
import logging
import requests
from typing import Dict, Any, Optional, List, Union, Callable, Iterator
import time

from src.config.settings import LLM_SERVER

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
        
        IMPORTANT: Always use the available tools to perform actions. DO NOT just suggest what to do - 
        call the appropriate tool function instead. For example, instead of saying "I should move forward", 
        call the move_forward tool with an appropriate speed.
        
        When thinking through your decision, briefly include your reasoning BEFORE calling any tools.
        Your reasoning should be 1-2 short sentences, followed by the appropriate tool call.
        
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
            Dict: Response chunks from the LLM.
        """
        prompt = self._prepare_prompt(sensor_data, camera_data, custom_prompt)
        prepared_tools = self._prepare_tools(tools)
        
        # Buffer for accumulating the complete response
        complete_response = ""
        response_count = 0
        
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
                                    # Log the actual text response from the LLM for debugging
                                    logger.debug(f"LLM chunk: {chunk.get('response', '')}")
                                
                                # Create a chunk result with the raw data
                                chunk_result = {
                                    "raw_chunk": chunk,
                                    "complete": chunk.get("done", False),
                                    "text": chunk.get("response", "")
                                }
                                
                                # Log tool calls if present in the chunk
                                if "tool_calls" in chunk:
                                    logger.info(f"Streaming chunk contains {len(chunk['tool_calls'])} tool calls")
                                    chunk_result["tool_calls"] = chunk["tool_calls"]
                                
                                # Call the callback if provided
                                if callback:
                                    callback(chunk_result)
                                
                                # Yield the chunk result
                                yield chunk_result
                                
                                # If done, break the loop
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON from streaming response: {line_str}")
                else:
                    error_msg = f"Error from LLM API: {response.status_code}"
                    logger.error(error_msg)
                    yield {"error": error_msg}
                    
            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"LLM streaming response completed in {elapsed_time:.2f} seconds ({response_count} chunks)")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            yield {"error": error_msg}
        except Exception as e:
            error_msg = f"Error processing LLM response: {str(e)}"
            logger.error(error_msg)
            yield {"error": error_msg}
        
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
            Dict: Response from the LLM with tool calls or text.
        """
        prompt = self._prepare_prompt(sensor_data, camera_data, custom_prompt)
        prepared_tools = self._prepare_tools(tools)
        
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
                    # Truncate response for logging if it's too long
                    response_preview = result["response"][:200]
                    if len(result["response"]) > 200:
                        response_preview += "..."
                    logger.debug(f"Response preview: {response_preview}")
                    
                    # Log the full response at INFO level for monitoring
                    logger.info(f"LLM full response: {result['response']}")
                
                # Check for tool calls in the response
                if "tool_calls" in result:
                    logger.info(f"LLM returned {len(result['tool_calls'])} tool calls")
                    return {
                        "tool_calls": result["tool_calls"],
                        "raw_response": result.get("response", "")
                    }
                
                # If no tool calls, just return the text response
                return {
                    "text": result.get("response", "").strip(),
                    "raw_response": result.get("response", "")
                }
            else:
                logger.error(f"Error from LLM API: {response.status_code} - {response.text}")
                return {"error": f"API Error: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            return {"error": f"Processing error: {str(e)}"}
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the LLM response text.
        
        Args:
            response_text (str): The raw text response from the LLM.
            
        Returns:
            Dict: Basic parsed response.
        """
        # The LLM is now instructed to use tool calls directly, 
        # so we don't need to parse JSON from the response anymore.
        # Just return a simple dict with the text
        return {
            "text": response_text.strip(),
            "raw_response": response_text
        }
    
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