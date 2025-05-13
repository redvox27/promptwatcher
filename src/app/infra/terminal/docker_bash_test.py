"""Test script for verifying Docker socket access using direct bash commands."""

import logging
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def run_command(command: str) -> tuple:
    """
    Run a shell command and return its output and exit code.
    
    Args:
        command: The command to run
        
    Returns:
        tuple: (stdout, stderr, return_code)
    """
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return_code = process.returncode
    
    return stdout, stderr, return_code


def test_docker_socket_access() -> bool:
    """
    Test if Docker socket is accessible.
    
    Returns:
        bool: True if docker socket is accessible, False otherwise
    """
    command = "ls -la /var/run/docker.sock"
    stdout, stderr, return_code = run_command(command)
    
    if return_code != 0:
        logger.error(f"Error checking Docker socket: {stderr}")
        return False
    
    logger.info(f"Docker socket info: {stdout}")
    return True


def test_docker_version() -> bool:
    """
    Test getting Docker version via socket.
    
    Returns:
        bool: True if docker version command works, False otherwise
    """
    command = "curl -s --unix-socket /var/run/docker.sock http://localhost/version"
    stdout, stderr, return_code = run_command(command)
    
    if return_code != 0:
        logger.error(f"Error getting Docker version: {stderr}")
        return False
    
    logger.info(f"Docker version info: {stdout}")
    return True


def test_list_containers() -> bool:
    """
    Test listing containers via Docker socket.
    
    Returns:
        bool: True if listing containers works, False otherwise
    """
    command = "curl -s --unix-socket /var/run/docker.sock http://localhost/containers/json"
    stdout, stderr, return_code = run_command(command)
    
    if return_code != 0:
        logger.error(f"Error listing containers: {stderr}")
        return False
    
    logger.info(f"Container list response length: {len(stdout)} characters")
    return True


def test_privileged_command() -> bool:
    """
    Test running a privileged command via Docker.
    
    Returns:
        bool: True if privileged command works, False otherwise
    """
    command = "docker run --rm --privileged --pid=host alpine ps aux"
    stdout, stderr, return_code = run_command(command)
    
    if return_code != 0:
        logger.error(f"Error running privileged command: {stderr}")
        return False
    
    logger.info(f"Process list contains {stdout.count(chr(10))} lines")
    return True


def run_all_tests() -> bool:
    """
    Run all Docker socket tests.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    tests = [
        ("Docker Socket Access", test_docker_socket_access),
        ("Docker Version", test_docker_version),
        ("List Containers", test_list_containers),
        ("Privileged Command", test_privileged_command),
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
    logger.info("Starting Docker socket access tests (bash version)")
    success = run_all_tests()
    
    if success:
        logger.info("All tests passed! Docker socket access is working.")
        sys.exit(0)
    else:
        logger.error("Tests failed! Docker socket access is not working properly.")
        sys.exit(1)