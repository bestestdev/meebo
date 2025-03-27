#!/usr/bin/env python3
"""
Tests for the LLM client with mock responses
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.brain.llm_client import LLMClient


class MockResponse:
    """Mock response object for requests."""
    
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
        
    def json(self):
        """Return mock JSON data."""
        return self.json_data


class TestLLMClient(unittest.TestCase):
    """Test the LLM client with mocked responses."""

    def setUp(self):
        """Set up test environment."""
        self.client = LLMClient(host="localhost", port=11434, model="qwen2:7b")

    @patch('requests.post')
    def test_process_basic_query(self, mock_post):
        """Test processing a basic query."""
        # Set up mock response
        mock_response = MockResponse({
            "model": "qwen2:7b",
            "created_at": "2023-01-01T00:00:00Z",
            "response": '{"thoughts": "The robot is in a clear area.", "actions": [{"type": "move", "params": {"direction": "forward", "speed": 50}}], "status": "operational"}',
            "done": True,
            "context": [1, 2, 3],  # Mock context
            "total_duration": 125000000,
            "load_duration": 5000000,
            "prompt_eval_duration": 20000000,
            "eval_count": 20,
            "eval_duration": 100000000
        }, 200)
        
        # Configure the mock to return the mock response
        mock_post.return_value = mock_response
        
        # Test basic processing
        response = self.client.process(
            sensor_data={"ir_sensors": {"front_left": False, "front_right": False}},
            camera_data={"has_frame": True}
        )
        
        # Verify mock was called correctly
        mock_post.assert_called_once()
        
        # Check that the response was parsed correctly
        self.assertEqual(response["thoughts"], "The robot is in a clear area.")
        self.assertEqual(len(response["actions"]), 1)
        self.assertEqual(response["actions"][0]["type"], "move")
        self.assertEqual(response["actions"][0]["params"]["direction"], "forward")
        self.assertEqual(response["status"], "operational")

    @patch('requests.post')
    def test_process_error_response(self, mock_post):
        """Test processing an error response."""
        # Set up mock error response
        mock_post.return_value = MockResponse({
            "error": "model not found"
        }, 404)
        
        # Test processing with error
        response = self.client.process(
            custom_prompt="test prompt"
        )
        
        # Check error handling
        self.assertIn("error", response)
        self.assertIn("API Error", response["error"])

    @patch('requests.post')
    def test_json_parsing_error(self, mock_post):
        """Test handling of malformed JSON response."""
        # Set up mock with malformed JSON
        mock_response = MockResponse({
            "model": "qwen2:7b",
            "response": "This is not valid JSON",
            "done": True
        }, 200)
        
        # Configure mock
        mock_post.return_value = mock_response
        
        # Test processing
        response = self.client.process(
            custom_prompt="test prompt"
        )
        
        # Check that we got a fallback response
        self.assertEqual(response["thoughts"], "Failed to parse response as JSON")
        self.assertEqual(response["actions"][0]["type"], "speak")

    @patch('requests.post')
    def test_json_with_markdown_formatting(self, mock_post):
        """Test parsing JSON from a markdown code block."""
        # Set up mock with JSON in markdown code block
        mock_response = MockResponse({
            "model": "qwen2:7b",
            "response": '```json\n{"thoughts": "I see an obstacle.", "actions": [{"type": "stop", "params": {}}], "status": "caution"}\n```',
            "done": True
        }, 200)
        
        # Configure mock
        mock_post.return_value = mock_response
        
        # Test processing
        response = self.client.process(
            custom_prompt="test prompt"
        )
        
        # Check parsing of code block
        self.assertEqual(response["thoughts"], "I see an obstacle.")
        self.assertEqual(response["actions"][0]["type"], "stop")
        self.assertEqual(response["status"], "caution")


if __name__ == "__main__":
    unittest.main() 