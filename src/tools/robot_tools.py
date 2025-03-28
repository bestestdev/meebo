"""Robot tool definitions."""

# Define robot tools
ROBOT_TOOLS = [
    # Information retrieval tools
    {
        "type": "function",
        "function": {
            "name": "get_motor_status",
            "description": "Get the current status of the robot's motors",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_battery",
            "description": "Check the robot's battery level",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    
    # Movement action tools
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
            "name": "move_backward",
            "description": "Move the robot backward at the specified speed",
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
            "name": "turn_right",
            "description": "Turn the robot right at the specified speed",
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
            "name": "stop",
            "description": "Stop all robot movement",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    
    # Audio and sensor tools
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
    },
    {
        "type": "function",
        "function": {
            "name": "listen",
            "description": "Listen for a voice command with a timeout",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Number of seconds to listen before timing out",
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_image",
            "description": "Capture an image from the robot's camera",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
] 