import logging
import time
import threading
import queue
import random
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from src.config.settings import AUDIO, IS_RASPBERRY_PI
from src.utils.logger import SimulatedLogger

logger = logging.getLogger(__name__)

class AudioManager:
    """
    Manager for the robot's audio capabilities.
    Handles both input (microphone) and output (speaker).
    """
    
    def __init__(self, simulation_mode=None):
        """
        Initialize the audio manager.
        
        Args:
            simulation_mode (bool, optional): Whether to use simulated audio devices.
                If None, determined based on hardware detection.
        """
        # Determine simulation mode based on hardware if not specified
        if simulation_mode is None:
            self.simulation_mode = not IS_RASPBERRY_PI
        else:
            self.simulation_mode = simulation_mode
            
        # Audio configuration
        self.audio_config = AUDIO
        
        # For audio recording and processing
        self.recording = False
        self.audio_queue = queue.Queue()
        self.record_thread = None
        self.process_thread = None
        
        # For audio playback
        self.playing = False
        self.play_thread = None
        
        # For speech recognition
        self.recognition_enabled = False
        self.last_transcript = ""
        
        # Last spoken text
        self.last_spoken_text = ""
        
        if self.simulation_mode:
            self.sim_logger = SimulatedLogger("audio")
            self.sim_logger.info("Initializing simulated audio devices")
        else:
            logger.info("Initializing physical audio devices")
            
        # Initialize audio devices
        self._init_audio_devices()
        
        logger.info(f"Audio manager initialized (simulation: {self.simulation_mode})")
    
    def _init_audio_devices(self):
        """Initialize audio input and output devices."""
        if not self.simulation_mode:
            try:
                # Try to import audio libraries
                import sounddevice as sd
                import numpy as np
                
                # Get audio device info
                devices = sd.query_devices()
                
                # Find suitable input and output devices
                input_device = self.audio_config["input_device"]
                output_device = self.audio_config["output_device"]
                
                # If no specific devices configured, try to find defaults
                if input_device is None:
                    for i, device in enumerate(devices):
                        if device["max_input_channels"] > 0:
                            input_device = i
                            break
                
                if output_device is None:
                    for i, device in enumerate(devices):
                        if device["max_output_channels"] > 0:
                            output_device = i
                            break
                
                self.audio_config["input_device"] = input_device
                self.audio_config["output_device"] = output_device
                
                if input_device is not None:
                    logger.info(f"Using audio input device: {devices[input_device]['name']}")
                else:
                    logger.warning("No audio input device found")
                    
                if output_device is not None:
                    logger.info(f"Using audio output device: {devices[output_device]['name']}")
                else:
                    logger.warning("No audio output device found")
                
            except ImportError:
                logger.error("Failed to import sounddevice. Falling back to simulation mode.")
                self.simulation_mode = True
                self.sim_logger = SimulatedLogger("audio")
            except Exception as e:
                logger.error(f"Error initializing audio devices: {str(e)}")
                logger.warning("Falling back to simulation mode")
                self.simulation_mode = True
                self.sim_logger = SimulatedLogger("audio")
    
    def start_listening(self, callback=None):
        """
        Start listening for audio input.
        
        Args:
            callback (callable, optional): Callback function to process audio chunks.
        """
        if self.recording:
            logger.warning("Already recording audio")
            return False
            
        self.recording = True
        
        if self.simulation_mode:
            self.sim_logger.info("Started simulated audio recording")
            # Start a thread that simulates audio recording
            self.record_thread = threading.Thread(
                target=self._simulate_audio_recording,
                args=(callback,)
            )
            self.record_thread.daemon = True
            self.record_thread.start()
            return True
        else:
            try:
                import sounddevice as sd
                import numpy as np
                
                def audio_callback(indata, frames, time, status):
                    """Callback for sounddevice to process audio chunks."""
                    if status:
                        logger.warning(f"Audio status: {status}")
                    
                    # Put audio data in queue
                    self.audio_queue.put(indata.copy())
                    
                    # Call user callback if provided
                    if callback:
                        callback(indata)
                
                # Start the stream
                self.stream = sd.InputStream(
                    samplerate=self.audio_config["sample_rate"],
                    channels=self.audio_config["channels"],
                    device=self.audio_config["input_device"],
                    callback=audio_callback
                )
                self.stream.start()
                
                logger.info(f"Started audio recording (sample rate: {self.audio_config['sample_rate']})")
                return True
                
            except Exception as e:
                logger.error(f"Error starting audio recording: {str(e)}")
                self.recording = False
                return False
    
    def _simulate_audio_recording(self, callback=None):
        """
        Simulate audio recording in a thread.
        
        Args:
            callback (callable, optional): Callback function to process simulated audio.
        """
        try:
            import numpy as np
            
            self.sim_logger.info("Simulated audio recording started")
            
            while self.recording:
                # Generate synthetic audio chunks (silence with occasional "peaks")
                chunk_size = int(self.audio_config["sample_rate"] * 0.1)  # 100ms chunks
                channels = self.audio_config["channels"]
                
                # Generate mostly silence with occasional "noise"
                if random.random() < 0.1:  # 10% chance of "noise"
                    # Generate synthetic audio (white noise with decreasing amplitude)
                    synthetic_audio = np.random.randn(chunk_size, channels) * 0.1
                else:
                    # Generate silence with a tiny bit of noise
                    synthetic_audio = np.random.randn(chunk_size, channels) * 0.001
                
                # Put in queue
                self.audio_queue.put(synthetic_audio)
                
                # Call user callback if provided
                if callback:
                    callback(synthetic_audio)
                
                # Sleep to simulate real-time audio
                time.sleep(0.1)
                
            self.sim_logger.info("Simulated audio recording stopped")
            
        except ImportError:
            self.sim_logger.warning("NumPy not available for audio simulation")
            self.recording = False
    
    def stop_listening(self):
        """Stop listening for audio input."""
        if not self.recording:
            return
            
        self.recording = False
        
        if self.simulation_mode:
            self.sim_logger.info("Stopped simulated audio recording")
            # Wait for the simulation thread to end
            if self.record_thread and self.record_thread.is_alive():
                self.record_thread.join(timeout=1.0)
        else:
            try:
                # Stop the audio stream
                if hasattr(self, 'stream'):
                    self.stream.stop()
                    self.stream.close()
                logger.info("Audio recording stopped")
            except Exception as e:
                logger.error(f"Error stopping audio recording: {str(e)}")
    
    def say(self, text, wait=True):
        """
        Speak the given text through the audio output.
        
        Args:
            text (str): Text to speak.
            wait (bool): Whether to wait for the speech to complete.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        self.last_spoken_text = text
        
        if self.simulation_mode:
            self.sim_logger.info(f"Simulated speech: {text}")
            time.sleep(len(text) * 0.05)  # Simulate speech time
            return True
        else:
            try:
                # Check for text-to-speech libraries
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    
                    if wait:
                        # Speak synchronously
                        engine.say(text)
                        engine.runAndWait()
                    else:
                        # Start a thread for asynchronous speech
                        def speak_thread():
                            engine = pyttsx3.init()
                            engine.say(text)
                            engine.runAndWait()
                            
                        self.play_thread = threading.Thread(target=speak_thread)
                        self.play_thread.daemon = True
                        self.play_thread.start()
                        
                    logger.info(f"Speaking: {text}")
                    return True
                    
                except ImportError:
                    # Try alternate TTS methods
                    if IS_RASPBERRY_PI:
                        # On Raspberry Pi, try using espeak
                        import subprocess
                        cmd = ["espeak", text]
                        
                        if wait:
                            subprocess.run(cmd, check=True)
                        else:
                            subprocess.Popen(cmd)
                            
                        logger.info(f"Speaking with espeak: {text}")
                        return True
                    else:
                        logger.error("No text-to-speech library available")
                        return False
                        
            except Exception as e:
                logger.error(f"Error during speech synthesis: {str(e)}")
                return False
    
    def listen_for_command(self, timeout=5.0):
        """
        Listen for a voice command and return the recognized text.
        
        Args:
            timeout (float): Maximum time to listen in seconds.
            
        Returns:
            str: Recognized text, or empty string if nothing recognized.
        """
        if self.simulation_mode:
            self.sim_logger.info(f"Simulated voice command recognition (timeout: {timeout}s)")
            
            # Simulate thinking time
            time.sleep(random.uniform(0.5, min(2.0, timeout)))
            
            # Occasionally return a simulated command
            if random.random() < 0.8:  # 80% chance of "recognizing" something
                commands = [
                    "move forward",
                    "turn left",
                    "turn right",
                    "stop",
                    "what do you see",
                    "hello robot"
                ]
                recognized = random.choice(commands)
                self.sim_logger.info(f"Simulated recognition result: '{recognized}'")
                self.last_transcript = recognized
                return recognized
            else:
                self.sim_logger.info("Simulated recognition: No speech detected")
                return ""
        else:
            try:
                import speech_recognition as sr
                
                recognizer = sr.Recognizer()
                
                logger.info(f"Listening for command (timeout: {timeout}s)")
                
                with sr.Microphone(device_index=self.audio_config["input_device"]) as source:
                    # Adjust for ambient noise
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    # Listen for audio
                    audio = recognizer.listen(source, timeout=timeout)
                    
                    try:
                        # Recognize speech using Google Speech Recognition
                        recognized = recognizer.recognize_google(audio)
                        logger.info(f"Recognized: '{recognized}'")
                        self.last_transcript = recognized
                        return recognized
                    except sr.UnknownValueError:
                        logger.info("Google Speech Recognition could not understand audio")
                        return ""
                    except sr.RequestError as e:
                        logger.error(f"Could not request results from Google Speech Recognition service: {e}")
                        return ""
                    except Exception as e:
                        logger.error(f"Error during speech recognition: {e}")
                        return ""
            except ImportError:
                logger.error("Speech recognition library not available")
                return ""
            except Exception as e:
                logger.error(f"Error setting up speech recognition: {e}")
                return ""
    
    def play_sound(self, sound_file=None, wait=True):
        """
        Play a sound file.
        
        Args:
            sound_file (str): Path to sound file to play.
            wait (bool): Whether to wait for the sound to complete.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if self.simulation_mode:
            duration = random.uniform(0.5, 2.0)
            self.sim_logger.info(f"Simulated sound playback: {sound_file} ({duration:.1f}s)")
            
            if wait:
                time.sleep(duration)
            
            return True
        else:
            try:
                from pydub import AudioSegment
                from pydub.playback import play
                
                if not sound_file or not os.path.exists(sound_file):
                    logger.error(f"Sound file not found: {sound_file}")
                    return False
                
                # Load sound file
                sound = AudioSegment.from_file(sound_file)
                
                if wait:
                    # Play synchronously
                    play(sound)
                    logger.info(f"Played sound: {sound_file}")
                else:
                    # Play in a thread
                    def play_thread(sound):
                        play(sound)
                        
                    self.play_thread = threading.Thread(target=play_thread, args=(sound,))
                    self.play_thread.daemon = True
                    self.play_thread.start()
                    logger.info(f"Started playing sound: {sound_file}")
                    
                return True
                
            except ImportError:
                logger.error("pydub not available for audio playback")
                return False
            except Exception as e:
                logger.error(f"Error playing sound: {str(e)}")
                return False
    
    def get_audio_devices(self):
        """
        Get a list of available audio devices.
        
        Returns:
            list: List of audio device information dictionaries.
        """
        if self.simulation_mode:
            # Return simulated devices
            return [
                {"name": "Simulated Microphone", "input_channels": 1, "output_channels": 0},
                {"name": "Simulated Speaker", "input_channels": 0, "output_channels": 2}
            ]
        else:
            try:
                import sounddevice as sd
                devices = sd.query_devices()
                return list(devices)
            except ImportError:
                logger.error("sounddevice not available")
                return []
            except Exception as e:
                logger.error(f"Error getting audio devices: {str(e)}")
                return []
    
    def cleanup(self):
        """Clean up audio resources."""
        # Stop listening if active
        self.stop_listening()
        
        # Stop any ongoing speech
        if self.play_thread and self.play_thread.is_alive():
            # Can't really stop the thread, but we can wait for it to finish
            self.play_thread.join(timeout=0.5)
            
        logger.info("Audio resources cleaned up") 