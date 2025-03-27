#!/usr/bin/env python3
"""
Example showing how to use tool calls for all robot actions.
Pure tool-based system with no legacy action format compatibility.
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

# Define action tools
ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "move_forward",
            "description": "Move the robot forward at the specified speed",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "integer",
                        "description": "Speed from 0-100 with 100 being the fastest",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["speed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "turn_left",
            "description": "Turn the robot left at the specified speed",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "integer",
                        "description": "Speed from 0-100 with 100 being the fastest",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["speed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speak",
            "description": "Have the robot speak the provided text",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text for the robot to say"
                    },
                    "wait": {
                        "type": "boolean",
                        "description": "Whether to wait for speech to complete before continuing (default: false)"
                    }
                },
                "required": ["text"]
            }
        }
    }
]

def handle_tool_calls(tool_calls):
    """Handle any tool calls returned by the LLM."""
    if not tool_calls:
        print("No tool calls received.")
        return []
        
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
            
            # Simulate execution
            if function_name == "move_forward":
                speed = function_args.get("speed", 50)
                result = {"action": "move_forward", "speed": speed, "status": "executed"}
                print(f"🔄 EXECUTED: move_forward with speed {speed}")
            elif function_name == "turn_left":
                speed = function_args.get("speed", 50)
                result = {"action": "turn_left", "speed": speed, "status": "executed"}
                print(f"🔄 EXECUTED: turn_left with speed {speed}")
            elif function_name == "speak":
                text = function_args.get("text", "")
                wait = function_args.get("wait", False)
                result = {"action": "speak", "text": text, "wait": wait, "status": "executed"}
                print(f"🔊 EXECUTED: speak '{text}'")
            else:
                result = {"error": f"Unknown function: {function_name}"}
                print(f"❌ ERROR: Unknown function '{function_name}'")
            
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
    if "text" in chunk and chunk["text"]:
        # Print the text part of the chunk
        print(chunk["text"], end="", flush=True)
    
    # Check for tool calls in this chunk
    if "raw_chunk" in chunk and "tool_calls" in chunk["raw_chunk"]:
        tool_calls = chunk["raw_chunk"]["tool_calls"]
        if tool_calls:
            function_name = tool_calls[0]["function"]["name"]
            print(f"\n🛠️  Tool Call: {function_name}")
    
    # Check if this is the final chunk
    if chunk.get("complete", False):
        print("\n--- Response complete ---")

def run_example():
    """Run the example to demonstrate tool-based actions."""
    # Create a client
    client = LLMClient()
    
    # Simulated sensor data
    sensor_data = {
        "distance": 120,  # cm
        "temperature": 22.5,  # celsius
        "light_level": 75,  # percent
        "motion_detected": False
    }
    
    print("\n===== PURE TOOL-BASED SYSTEM EXAMPLE =====")
    print("Using only tool calls for all robot actions\n")
    
    print("🤖 SCENARIO 1: Obstacle Avoidance")
    result = client.process(
        sensor_data=sensor_data,
        custom_prompt="There's an obstacle ahead. Please move left to avoid it and announce what you're doing.",
        tools=ACTION_TOOLS
    )
    
    # Display LLM's thinking
    if "text" in result:
        print("\nLLM's thinking:")
        print(result["text"])
    
    # Handle any tool calls
    print("\nTool calls:")
    if "tool_calls" in result:
        handle_tool_calls(result["tool_calls"])
    else:
        print("No tool calls received, but expected some.")
    
    print("\n🤖 SCENARIO 2: Person Greeting (Streaming)")
    print("Streaming response:")
    
    # Accumulate complete response for tool handling
    complete_response = {}
    
    # Use streaming process with tools
    for chunk in client.process_streaming(
        sensor_data=sensor_data,
        custom_prompt="I see a person. Drive forward to greet them and say hello.",
        tools=ACTION_TOOLS,
        callback=streaming_callback
    ):
        # Save the final complete response for tool handling
        if chunk.get("complete", False):
            complete_response = chunk
    
    # Handle any tool calls in the complete response
    print("\nFinal tool calls execution:")
    if "raw_chunk" in complete_response and "tool_calls" in complete_response["raw_chunk"]:
        handle_tool_calls(complete_response["raw_chunk"]["tool_calls"])
    else:
        print("No tool calls in the final response.")

if __name__ == "__main__":
    run_example() 