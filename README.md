# Meebo the LLM-Powered Robot

This project implements an AI-driven robot using a local LLM (Qwen2.5:7b) as its "brain" with a Raspberry Pi handling sensor input and motor control.

## Components

### Hardware
- Raspberry Pi Compute Module 5 with Nano Base Board (running Raspberry Pi Server OS - headless)
- 4 IR obstacle avoidance modules
- TT DC geared motors with wheels
- PCA9685PW 16-channel PWM controller for PWM signal generation
- L298N dual H-bridge motor driver for DC motor control
- MAX98357 I2S Class-D Mono Amplifier for audio output
- GY-MAX4466 Electret Microphone Amplifier for audio input
- ADS1115 ADC for analog input processing
- Small PC speaker (connected to the MAX98357)
- Ultrasonic module
- IMX219 8MP Camera Module with MIPI-CSI interface and 120° FOV
- Zeee 4S 6000mAh LiPo battery (14.8V) with buck converters

### Software
- Dedicated server running Ollama with Qwen2.5:7b model
- Python-based control system on the Raspberry Pi
- Network communication over private LAN
- Streaming capabilities for real-time LLM interaction
- Computer vision processing for camera input
- Speech recognition and audio processing
- Tool-based action system for robot control

## Architecture

The system uses a client-server architecture:
- **Server**: A dedicated, more powerful machine running Ollama and the Qwen2.5:7b model
- **Client**: Raspberry Pi CM5 that handles all sensor input, audio I/O, and motor control
- Communication happens over a private network connection

## Development Setup

### Setting Up the Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/meebo.git
   cd meebo
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Ollama server**:
   - Install Ollama from [https://ollama.ai/](https://ollama.ai/)
   - Pull the Qwen2.5:7b model:
     ```bash
     ollama pull qwen2:7b
     ```
   - Start the Ollama server:
     ```bash
     ollama serve
     ```

5. **Configure environment variables**:
   Create a `.env` file in the root directory with the following variables:
   ```
   LLM_HOST=localhost
   LLM_PORT=11434
   LLM_MODEL=qwen2.5:7b
   MEEBO_DEV_MODE=true
   ```

### Running in Development Mode

The project can run in development mode on a non-Raspberry Pi system, using simulated hardware:

```bash
# Run with default settings (will auto-detect dev mode on non-Pi systems)
python3 src/main.py

# Explicitly run in development mode
python3 src/main.py --dev

# Set logging level
python3 src/main.py --dev --log-level=DEBUG

# Run in interactive mode (enables voice command detection)
python3 src/main.py --dev --interactive
```

#### Command Line Options

- `--dev`: Enable development mode (simulated hardware)
- `--log-level=LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--interactive`: Enable interactive mode with voice command recognition

#### Operation Modes

- **Standard Mode**: The robot autonomously processes sensor data and makes decisions
- **Interactive Mode**: Additionally listens for voice commands every few seconds

In development mode:
- All hardware components are simulated
- The LLM client connects to the configured Ollama server
- Sensors return simulated readings
- Motors log movement commands instead of controlling hardware
- Camera provides simulated frames with randomized "objects"
- Audio input/output is simulated

### Testing the Tool-Based System

Try out the examples to see how the different features work:

```bash
# Run the streaming and tool use example
python3 examples/streaming_tool_example.py

# Run the action tools example (showing how all robot actions use tool calls)
python3 examples/action_tools_example.py
```

These examples demonstrate:
1. Non-streaming responses with tools
2. Streaming responses with tools (real-time output)
3. Using tool calls for all robot actions (movement, speech, etc.)
4. Handling tool call results

### Project Structure

```
meebo/
├── docs/                # Documentation
├── logs/                # Log files (generated at runtime)
├── examples/            # Example scripts for specific features
├── src/                 # Source code
│   ├── brain/           # LLM integration and decision making
│   ├── sensors/         # Sensor input processing
│   ├── actuators/       # Motor and movement control
│   ├── audio/           # Audio input/output
│   ├── vision/          # Camera and visual processing
│   ├── utils/           # Utility functions
│   ├── config/          # Configuration files
│   └── main.py          # Main entry point
├── tests/               # Unit tests
├── requirements.txt     # Python dependencies
├── setup.py             # Package setup
└── README.md            # This file
```

## Action System

Meebo uses a pure tool-based action system that allows the LLM to call functions that execute actions on the robot. All robot capabilities are exposed as tools, providing a consistent interface for the LLM to interact with the robot's hardware.

### Pure Tool-Based Architecture

The system exclusively uses LLM tool calls (function calling) for all robot actions, with these key benefits:
- **Consistency**: All operations use the same tool-calling pattern
- **Type Safety**: Tool parameters include type definitions and validation
- **Streaming Compatibility**: Tool calls can be extracted from streaming responses
- **Better Prompting**: The LLM is instructed to use tools directly rather than outputting JSON

To see this in action, try the example:
```bash
python3 examples/action_tools_example.py
```

### Core Action Tools

The following tools control the robot's movement and interactions:

- **move_forward**: Move the robot forward
  ```json
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
  }
  ```

- **move_backward**: Move the robot backward
- **turn_left**: Turn the robot left
- **turn_right**: Turn the robot right
- **stop**: Stop all movement
- **speak**: Convert text to speech
- **listen**: Listen for voice commands
- **capture_image**: Take a picture with the camera

### Information Tools

These tools retrieve information about the robot's state:

- **get_motor_status**: Get the current motor speeds and directions
  ```json
  {
    "type": "function",
    "function": {
      "name": "get_motor_status",
      "description": "Get the current status of robot's motors",
      "parameters": {}
    }
  }
  ```

- **check_battery**: Check the robot's battery level

## Streaming Responses

The LLM client supports streaming responses, allowing for real-time feedback and improved responsiveness:

- Real-time token generation from the LLM
- Immediate tool calls appear in the stream as soon as the LLM decides to use them
- Tool calls can be executed immediately, even before the complete response is finished
- Better user experience with continuous feedback

## Production Deployment

Instructions for deploying on the Raspberry Pi hardware will be provided once the development phase is complete.

## Project Goal

The goal is to create a robot that can:
1. Navigate its environment using IR and ultrasonic sensors
2. Respond to voice commands via the microphone
3. Provide audio feedback through the speaker
4. Make autonomous decisions using the LLM running on the server
5. Process visual data from the wide-angle camera for enhanced environmental awareness
6. Act in real-time with streaming LLM responses and tool usage

## Implementation Plan

1. Set up Ollama and Qwen2.5:7b on the dedicated server
2. Configure network communication between the Raspberry Pi and server
3. Interface with all sensors, camera, and servos/motors on the Raspberry Pi
4. Set up the MAX98357 I2S audio amplifier and GY-MAX4466 microphone
5. Develop a streaming API to connect the robot's "senses" to the LLM
6. Create a control system that translates LLM decisions into physical actions
7. Implement voice input/output capabilities
8. Integrate computer vision processing for the camera feed

## Sensor Integration Strategy

The robot employs a multi-sensor approach for optimal environmental perception:
- **IR sensors**: For close-range obstacle detection and edge detection
- **Ultrasonic sensor**: For more reliable medium-range distance measurements
- **IMX219 Camera with 120° FOV**: For visual recognition, navigation, and object detection

## Audio System

The robot's audio system consists of:
- **Input**: GY-MAX4466 Electret Microphone Amplifier Module for capturing voice commands
- **Output**: MAX98357 I2S Class-D Mono Amplifier driving a small speaker
- **Processing**: The Raspberry Pi will handle basic audio processing with the more complex speech recognition performed on the server

This setup allows for low-latency audio capture and playback while offloading the CPU-intensive speech recognition and natural language processing to the more powerful server.

### Audio Hardware Configuration

#### Audio Output
The MAX98357 I2S audio amplifier provides digital audio output capabilities:
- Digital interface that connects directly to the Raspberry Pi's I2S pins
- Filterless Class-D operation with high efficiency
- 3.2W output into 4Ω speakers at 5V
- Simple setup with minimal external components

#### Audio Input
For audio input, the system uses:
- **GY-MAX4466 Microphone**: Electret microphone with adjustable gain
- **ADS1115 ADC**: 16-bit analog-to-digital converter for high-resolution audio capture

The GY-MAX4466 produces an analog signal that requires conversion to digital format. The ADS1115 ADC is used for this purpose with the following advantages:
- **High Resolution**: 16-bit precision provides excellent audio quality
- **I2C Interface**: Uses only two GPIO pins (SDA and SCL) plus power and ground
- **Programmable Gain**: Adjustable gain settings to optimize microphone signal quality
- **Multiple Channels**: Four input channels allow for additional analog sensors

#### Connection Diagram

To connect the microphone system:
1. **ADS1115 to Raspberry Pi**:
   - VDD → 3.3V
   - GND → GND
   - SCL → GPIO 3 (SCL)
   - SDA → GPIO 2 (SDA)

2. **GY-MAX4466 to ADS1115**:
   - VCC → 3.3V
   - GND → GND
   - OUT → A0 (or any analog input channel on the ADS1115)

### Software Configuration

Required software dependencies:
```bash
sudo apt-get update
sudo apt-get install python3-pip
sudo pip3 install adafruit-circuitpython-ads1x15
```

## Hardware Connection Guide

### Complete Connection Diagram

This section provides comprehensive connection instructions for all hardware components to the Raspberry Pi CM5.

#### Audio Components

1. **MAX98357 I2S Audio Amplifier**:
   - VIN → 5V
   - GND → GND
   - DIN → GPIO 21
   - BCLK → GPIO 18
   - LRCLK → GPIO 19
   - SD → Connect to speaker positive terminal
   - GND → Connect to speaker negative terminal

2. **ADS1115 + GY-MAX4466 Microphone** (as detailed above)
   - Enable I2C in `raspi-config` before use

#### Motion and Sensing Components

3. **IR Obstacle Avoidance Modules** (x4):
   - VCC → 3.3V
   - GND → GND
   - OUT → GPIO pins (e.g., GPIO 17, 27, 22, 23)

4. **PCA9685PW 16-Channel PWM Controller**:
   - VCC → 3.3V
   - GND → GND
   - SCL → GPIO 3 (SCL)
   - SDA → GPIO 2 (SDA)
   - V+ → 5-6V from buck converter
   - GND → Common ground

5. **L298N Motor Driver** (dual H-bridge):
   - VCC → 5V
   - GND → GND
   - ENA/ENB → Connect to PCA9685 PWM outputs (channels 0-1)
   - IN1, IN2, IN3, IN4 → Connect to GPIO pins (e.g., GPIO 5, 6, 13, 19)
   - OUT1, OUT2, OUT3, OUT4 → Connect to motors
   - 12V → Connect to battery via buck converter (5-6V)

6. **TT DC Geared Motors** (x4):
   - Connect to L298N outputs
   - Attach wheels to motor shafts

7. **Ultrasonic Module** (HC-SR04):
   - VCC → 5V
   - GND → GND
   - TRIG → GPIO 24
   - ECHO → GPIO 25 (via voltage divider: 1kΩ and 2kΩ resistors to protect GPIO)

8. **IMX219 Camera Module**:
   - Connect via MIPI-CSI camera port on the Raspberry Pi CM5 carrier board
   - Enable camera interface in `raspi-config`
   - Compatible with CM5's MIPI interface
   - 8MP resolution for detailed image capture
   - 120° FOV provides wide-angle view for navigation and object detection

### Power Management Recommendations

For stable operation:
- Use Zeee 4S 6000mAh LiPo battery (14.8V) as the main power source
- Use buck converters to step down voltage:
  - 5V/3A for Raspberry Pi
  - 5-6V for motor drivers and PCA9685
- Ensure common ground between all components
- Include a low-voltage alarm/cutoff to prevent LiPo over-discharge
- Add capacitors (100-220μF) across power rails to stabilize voltage

### Interface Setup

1. **Enable Required Interfaces**:
   ```bash
   sudo raspi-config
   ```
   
   Navigate to "Interface Options" and enable:
   - I2C (for ADS1115)
   - SPI (if needed)
   - Camera (for 200° FOV camera)
   - I2S (for audio)

2. **Test I2C Devices**:
   ```bash
   sudo apt-get install i2c-tools
   sudo i2cdetect -y 1
   ```

3. **GPIO Library Setup**:
   ```bash
   sudo apt-get install python3-pip
   sudo pip3 install RPi.GPIO
   sudo pip3 install adafruit-blinka
   sudo pip3 install adafruit-circuitpython-pca9685
   sudo pip3 install adafruit-circuitpython-servokit
   ```

### Wiring Best Practices

- Use color-coded wires to distinguish power, ground, and signal connections
- Consider using dupont connectors for easy disconnect/reconnect during testing
- Label all connections
- Secure loose wires with cable ties or management solutions
- Test each component individually before final assembly
- Use a breadboard for initial prototyping

### PCA9685PW Servo Controller Setup

The PCA9685PW is a 16-channel, 12-bit PWM controller that communicates over I2C. It provides several key advantages for servo control:

- **Protection**: Isolates the Raspberry Pi from servo electrical noise and current spikes
- **Simplicity**: Uses only two GPIO pins (I2C) to control up to 16 servos
- **Precision**: Provides more stable PWM signals than software PWM on the Pi
- **Power Management**: Separate power input for servos prevents voltage drops affecting the Pi

### L298N Motor Driver & DC Motors Setup

The L298N is a dual H-bridge motor driver that can control two DC motors independently. When paired with the PCA9685 PWM controller and TT geared motors, it provides several benefits:

- **Higher Torque**: TT geared motors deliver more torque than 9g servos, handling the robot's weight better
- **Speed Control**: PWM signals from PCA9685 through L298N enable precise speed control
- **Direction Control**: H-bridge design allows for forward/reverse motor operation
- **Protection**: Isolates the Raspberry Pi from motor electrical noise and current demands

#### Connection Setup

1. **PWM Control**: PCA9685 outputs PWM signals that connect to the L298N's ENA and ENB pins
2. **Direction Control**: Raspberry Pi GPIO pins connect to IN1, IN2, IN3, and IN4 pins on the L298N
3. **Motor Connection**: L298N outputs (OUT1-4) connect to the TT motors
4. **Power**: L298N receives 5-6V from buck converter for motors, with separate 5V logic power

## Getting Started

(Documentation to be expanded as the project progresses)
