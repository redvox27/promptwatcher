"""Integration test for terminal session detection."""

import logging
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.session_detector import TerminalSessionDetector

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def test_terminal_session_detection():
    """Test terminal session detection with real Docker socket."""
    try:
        # Initialize Docker client
        docker_client = DockerClient()
        if not docker_client.is_connected():
            logger.error("Docker client not connected")
            return False
        
        # Print raw ps output first for debugging
        logger.info("Getting raw ps output for debugging")
        try:
            raw_output = docker_client.run_in_host("ps auxww")
            logger.info(f"Raw ps output sample (first 5 lines):\n{raw_output.splitlines()[:5]}")
        except Exception as e:
            logger.error(f"Error getting raw ps output: {str(e)}")
        
        # Create session detector
        detector = TerminalSessionDetector(docker_client)
        
        # Get terminal sessions
        sessions = detector.list_terminal_sessions()
        
        # Log results
        logger.info(f"Found {len(sessions)} terminal sessions")
        
        # Print details of each session
        for i, session in enumerate(sessions):
            logger.info(f"Session {i+1}:")
            logger.info(f"  PID: {session.get('pid')}")
            logger.info(f"  User: {session.get('user')}")
            logger.info(f"  Terminal: {session.get('terminal')}")
            logger.info(f"  Command: {session.get('command')}")
            logger.info(f"  Start Time: {session.get('start_time')}")
            logger.info(f"  State: {session.get('state')}")
            
        # Get interactive sessions
        interactive_sessions = detector.list_terminal_sessions(interactive_only=True)
        logger.info(f"Found {len(interactive_sessions)} interactive terminal sessions")
        
        # Test with different ps command format
        logger.info("Testing with different ps command format")
        
        # Try with BSD-style ps (common on macOS)
        bsd_output = docker_client.run_in_host("ps -ef")
        logger.info(f"BSD-style ps sample:\n{bsd_output.splitlines()[:5]}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing terminal session detection: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Starting terminal session detection test")
    success = test_terminal_session_detection()
    
    if success:
        logger.info("Terminal session detection test passed")
        sys.exit(0)
    else:
        logger.error("Terminal session detection test failed")
        sys.exit(1)