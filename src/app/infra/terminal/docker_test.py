"""Test script for verifying Docker socket access."""

import logging
import sys
import os
from typing import List, Dict

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

# Try both import styles to handle different execution contexts
try:
    from app.infra.terminal.docker_client import DockerClient
except ImportError:
    try:
        from src.app.infra.terminal.docker_client import DockerClient
    except ImportError:
        # If running directly from this directory
        from docker_client import DockerClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def test_docker_connection() -> bool:
    """
    Test connection to Docker daemon.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = DockerClient()
        return client.is_connected()
    except Exception as e:
        logger.error(f"Error connecting to Docker: {str(e)}")
        return False


def test_host_command_execution() -> bool:
    """
    Test executing a command in host namespace.
    
    Returns:
        bool: True if command execution successful, False otherwise
    """
    try:
        client = DockerClient()
        if not client.is_connected():
            logger.error("Docker client not connected")
            return False
        
        # Run a simple command to list processes
        result = client.run_in_host("ps -ef | grep -i python")
        logger.info(f"Command output: {result}")
        return True
    except Exception as e:
        logger.error(f"Error executing host command: {str(e)}")
        return False


def run_all_tests() -> bool:
    """
    Run all Docker tests.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    tests = [
        ("Docker Connection", test_docker_connection),
        ("Host Command Execution", test_host_command_execution),
    ]
    
    all_passed = True
    
    for name, test_func in tests:
        logger.info(f"Running test: {name}")
        try:
            result = test_func()
            if result:
                logger.info(f"✅ Test passed: {name}")
            else:
                logger.error(f"❌ Test failed: {name}")
                all_passed = False
        except Exception as e:
            logger.error(f"❌ Test error: {name} - {str(e)}")
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    logger.info("Starting Docker access tests")
    success = run_all_tests()
    
    if success:
        logger.info("All tests passed! Docker socket access is working.")
        sys.exit(0)
    else:
        logger.error("Tests failed! Docker socket access is not working properly.")
        sys.exit(1)