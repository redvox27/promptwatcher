"""Integration test for terminal monitoring system."""

import asyncio
import logging
import os
import sys
import time
from typing import List

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.docker_client import DockerClient
from src.app.infra.terminal.session_detector import TerminalSessionDetector
from src.app.infra.terminal.terminal_device_identifier import TerminalDeviceIdentifier
from src.app.infra.terminal.session_tracking_service import SessionTrackingService, TerminalSession
from src.app.infra.terminal.terminal_output_capture import (
    TerminalOutputCapture, 
    TerminalOutputBuffer,
    TerminalOutputProcessor
)
from src.app.infra.terminal.terminal_monitor_coordinator import TerminalMonitorCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def run_integration_test():
    """Run the integration test for terminal monitoring."""
    try:
        logger.info("Starting terminal monitoring integration test")
        
        # 1. Initialize components
        docker_client = DockerClient()
        session_detector = TerminalSessionDetector(docker_client)
        device_identifier = TerminalDeviceIdentifier(docker_client)
        output_capture = TerminalOutputCapture(docker_client)
        output_processor = TerminalOutputProcessor()
        
        # 2. Test terminal session detection
        logger.info("Testing terminal session detection")
        sessions = session_detector.list_terminal_sessions(interactive_only=True)
        
        if sessions:
            logger.info(f"Found {len(sessions)} interactive terminal sessions")
            for i, session in enumerate(sessions):
                logger.info(f"Session {i+1}: PID={session['pid']}, User={session['user']}, Terminal={session['terminal']}")
        else:
            logger.warning("No interactive terminal sessions found")
        
        # 3. Test terminal device identification
        if sessions:
            test_pid = sessions[0]['pid']
            logger.info(f"Testing terminal device identification for PID {test_pid}")
            
            devices = device_identifier.get_terminal_devices(test_pid)
            if devices:
                logger.info(f"Found {len(devices)} terminal devices")
                for i, device in enumerate(devices):
                    logger.info(f"Device {i+1}: {device['device_path']}, FDs: {device['file_descriptors']}")
                    
                    # Test terminal readability
                    readable = device_identifier.is_terminal_readable(device['device_path'])
                    logger.info(f"Terminal {device['device_path']} readable: {readable}")
                    
                    # Test terminal type detection
                    term_type = device_identifier.get_terminal_type(device['device_path'])
                    logger.info(f"Terminal type: {term_type}")
            else:
                logger.warning(f"No terminal devices found for PID {test_pid}")
        
        # 4. Test session tracking service
        logger.info("Testing session tracking service")
        
        # Initialize tracking service with a fast scan interval
        tracking_service = SessionTrackingService(
            session_detector,
            device_identifier,
            scan_interval=1.0
        )
        
        # Set up event handlers for tracking
        active_sessions = []
        closed_sessions = []
        
        def on_new_session(session: TerminalSession):
            logger.info(f"New session detected: {session.id}, PID={session.pid}, User={session.user}")
            active_sessions.append(session)
        
        def on_session_closed(session: TerminalSession):
            logger.info(f"Session closed: {session.id}, PID={session.pid}, User={session.user}")
            closed_sessions.append(session)
            
        tracking_service.on_new_session = on_new_session
        tracking_service.on_session_closed = on_session_closed
        
        # Start tracking
        tracking_service.start_tracking()
        
        # Wait for a scan to complete
        logger.info("Waiting for session scanning...")
        await asyncio.sleep(2)
        
        # Check results
        all_sessions = tracking_service.get_all_sessions()
        logger.info(f"Tracking {len(all_sessions)} active sessions")
        
        # Stop tracking
        tracking_service.stop_tracking()
        
        # 5. Test terminal output capture
        logger.info("Testing terminal output capture")
        
        if all_sessions:
            # Select first active session for testing
            test_session = all_sessions[0]
            logger.info(f"Testing output capture for session {test_session.id}, PID={test_session.pid}")
            
            # Attempt to capture output from all readable devices
            for device in test_session.terminal_devices:
                if device.get("is_readable", False):
                    device_path = device.get("device_path")
                    logger.info(f"Capturing output from {device_path}")
                    
                    # Try to capture
                    capture_result = output_capture.capture_output(device_path, timeout=1.0)
                    
                    if not capture_result.is_error and capture_result.content:
                        logger.info(f"Captured {len(capture_result.content)} bytes")
                        
                        # Process the content
                        processing_result = output_processor.process_raw_capture(capture_result.content)
                        logger.info(f"Processed content, cleaned length: {len(processing_result.clean_text)}")
                        
                        # Check for Claude conversations
                        if processing_result.contains_claude_conversation:
                            logger.info(f"Found Claude conversation!")
                            for i, conv in enumerate(processing_result.claude_conversations):
                                logger.info(f"Conversation {i+1} length: {len(conv)}")
                                
                                # Try to extract messages
                                prompt, response = output_processor.extract_message_pair(conv)
                                logger.info(f"Extracted prompt: {prompt[:50]}...")
                                logger.info(f"Extracted response: {response[:50]}...")
                        else:
                            logger.info("No Claude conversations found")
                    else:
                        logger.warning(f"Failed to capture output: {capture_result.error_message}")
        
        # 6. Test terminal monitor coordinator
        logger.info("Testing terminal monitor coordinator")
        
        # Initialize coordinator
        coordinator = TerminalMonitorCoordinator(
            docker_client,
            session_detector,
            device_identifier,
            tracking_service,
            output_capture=output_capture,
            output_processor=output_processor,
            settings={
                "project_name": "TestProject",
                "project_goal": "Testing",
                "monitoring_interval": 1.0,
                "capture_interval": 1.0,
                "buffer_size": 50000
            }
        )
        
        # Start a monitor
        monitor_id = coordinator.start_monitor()
        logger.info(f"Started monitor with ID {monitor_id}")
        
        # Wait for monitoring to start
        await asyncio.sleep(2)
        
        # Get monitor status
        status = coordinator.get_monitor_status(monitor_id)
        logger.info(f"Monitor status: {status.status.value}")
        logger.info(f"Active sessions: {len(status.active_sessions)}")
        
        # Stop the monitor
        success = coordinator.stop_monitor(monitor_id)
        logger.info(f"Stopped monitor: {success}")
        
        logger.info("Terminal monitoring integration test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in integration test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point for the test."""
    try:
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(run_integration_test())
        
        # Exit with appropriate status code
        if success:
            logger.info("Integration test passed")
            sys.exit(0)
        else:
            logger.error("Integration test failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()