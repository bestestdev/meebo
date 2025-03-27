#!/usr/bin/env python3
"""
Example showing streaming LLM responses and tool use with Meebo's brain.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any

# Add the parent directory to the Python path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brain.llm_client import LLMClient
from src.config.settings import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Define some example tools
EXAMPLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time for the robot",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "The format to return the time in (e.g., '24h' or '12h')",
                        "enum": ["24h", "12h"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_battery_level",
            "description": "Check the current battery level of the robot",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

def get_current_time(format="24h"):
    """Example tool implementation to get the current time."""
    from datetime import datetime
    if format == "12h":
        time_str = datetime.now().strftime("%I:%M:%S %p")
    else:
        time_str = datetime.now().strftime("%H:%M:%S")
    return {"time": time_str, "format": format}

def check_battery_level():
    """Example tool implementation to get a simulated battery level."""
    return {"level": 78, "status": "charging"}

def handle_tool_calls(tool_calls):
    """Handle any tool calls returned by the LLM."""
    results = []
    
    for tool_call in tool_calls:
        if "function" in tool_call:
            function_name = tool_call["function"]["name"]
            function_args = {}
            
            # Parse arguments if any
            if "arguments" in tool_call["function"]:
                try:
                    function_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse arguments: {tool_call['function']['arguments']}")
            
            # Execute the appropriate function
            if function_name == "get_current_time":
                result = get_current_time(**function_args)
            elif function_name == "check_battery_level":
                result = check_battery_level()
            else:
                result = {"error": f"Unknown function: {function_name}"}
            
            # Add to results
            results.append({
                "tool_call_id": tool_call.get("id", "unknown"),
                "function_name": function_name,
                "result": result
            })
    
    return results

def streaming_callback(chunk: Dict[str, Any]):
    """
    Callback function for streaming responses.
    
    Args:
        chunk: A chunk of the streaming response
    """
    if "raw_chunk" in chunk and "response" in chunk["raw_chunk"]:
        # Get just the new text from this chunk
        response_text = chunk["raw_chunk"]["response"]
        
        # Print the chunk in a readable way
        if response_text:
            print(response_text, end="", flush=True)
    
    # Check if this is the final chunk
    if chunk.get("complete", False):
        print("\n--- Response complete ---")

def run_example():
    """Run the example to demonstrate streaming and tool use."""
    # Create a client
    client = LLMClient()
    
    # Simulated sensor data
    sensor_data = {
        "distance": 120,  # cm
        "temperature": 22.5,  # celsius
        "light_level": 75,  # percent
        "motion_detected": False
    }
    
    print("\n===== NON-STREAMING EXAMPLE WITHOUT TOOLS =====")
    result = client.process(
        sensor_data=sensor_data,
        custom_prompt="Given the sensor data, what should I do? Respond in JSON format."
    )
    print(json.dumps(result, indent=2))
    
    print("\n===== NON-STREAMING EXAMPLE WITH TOOLS =====")
    result = client.process(
        sensor_data=sensor_data,
        custom_prompt="What time is it and what's my battery level? Use the available tools.",
        tools=EXAMPLE_TOOLS
    )
    print(json.dumps(result, indent=2))
    
    # If the response contains tool calls, handle them
    if "tool_calls" in result:
        tool_results = handle_tool_calls(result["tool_calls"])
        print("\nTool Results:")
        print(json.dumps(tool_results, indent=2))
        
        # You could feed the tool results back to the LLM for further processing here
    
    print("\n===== STREAMING EXAMPLE WITHOUT TOOLS =====")
    print("Streaming response:")
    
    # Use streaming process and handle the result chunks
    for _ in client.process_streaming(
        sensor_data=sensor_data,
        custom_prompt="Tell me three things I could do right now with my sensors. Respond in JSON format.",
        callback=streaming_callback
    ):
        # The callback handles printing
        pass
    
    print("\n===== STREAMING EXAMPLE WITH TOOLS =====")
    print("Streaming response with tools:")
    
    # Accumulate complete response for tool handling
    complete_response = {}
    
    # Use streaming process with tools
    for chunk in client.process_streaming(
        sensor_data=sensor_data,
        custom_prompt="What time is it and what's my battery level? Use the available tools.",
        tools=EXAMPLE_TOOLS,
        callback=streaming_callback
    ):
        # Save the final complete response for tool handling
        if chunk.get("complete", False):
            complete_response = chunk
    
    # Handle any tool calls in the complete response
    if "tool_calls" in complete_response:
        tool_results = handle_tool_calls(complete_response["tool_calls"])
        print("\nTool Results:")
        print(json.dumps(tool_results, indent=2))

if __name__ == "__main__":
    run_example() 