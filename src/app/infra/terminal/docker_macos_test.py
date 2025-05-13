#!/usr/bin/env python3
"""
Test script for Docker connection on macOS systems.
This script tries multiple connection methods to find what works.
"""

import os
import sys
import subprocess
import platform

def print_header(title):
    """Print a section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def test_docker_cli():
    """Test Docker CLI access."""
    print_header("Testing Docker CLI Access")
    
    print("Testing 'docker version'...")
    code, out, err = run_command("docker version")
    
    if code == 0:
        print("✅ Docker CLI is accessible")
        print(f"Docker version info (truncated):\n{out.split('Server:')[0]}")
        return True
    else:
        print("❌ Docker CLI is NOT accessible")
        print(f"Error: {err}")
        return False

def test_docker_socket():
    """Test Docker socket access."""
    print_header("Testing Docker Socket")
    
    socket_paths = [
        "/var/run/docker.sock",
        "/Users/vincentluder/.docker/run/docker.sock",
        os.path.expanduser("~/.docker/run/docker.sock")
    ]
    
    for socket_path in socket_paths:
        print(f"Checking if socket exists at: {socket_path}")
        if os.path.exists(socket_path):
            print(f"✅ Docker socket found at: {socket_path}")
            
            # Test socket access
            print(f"Testing socket permissions...")
            code, out, err = run_command(f"ls -la {socket_path}")
            print(f"Socket file info: {out.strip()}")
            
            # Try connecting using curl
            print("Testing socket connection with curl...")
            code, out, err = run_command(f"curl --unix-socket {socket_path} http://localhost/version")
            
            if code == 0:
                print("✅ Socket connection successful")
                print(f"Socket API response (truncated): {out[:100]}...")
                return True
            else:
                print(f"❌ Socket connection failed: {err}")
        else:
            print(f"❌ Docker socket not found at: {socket_path}")
    
    return False

def test_environment():
    """Test environment configuration."""
    print_header("Testing Environment Configuration")
    
    # Check OS
    print(f"Operating System: {platform.system()} {platform.release()}")
    
    # Check if we're in a container
    in_container = os.path.exists('/.dockerenv')
    print(f"Running in container: {'Yes' if in_container else 'No'}")
    
    # Check environment variables
    print("\nRelevant environment variables:")
    for var in ['DOCKER_HOST', 'DOCKER_SOCKET', 'DOCKER_API_VERSION', 'HOST_OS']:
        value = os.environ.get(var, 'Not set')
        print(f"  {var}: {value}")
    
    # Check Docker context
    print("\nDocker context:")
    run_command("docker context ls")

def suggest_fixes():
    """Suggest fixes for common issues."""
    print_header("Suggested Fixes")
    
    print("1. Ensure Docker Desktop is running")
    print("   - Open Docker Desktop application")
    print("   - Check the whale icon in the menu bar")
    
    print("\n2. Check Docker Desktop permissions")
    print("   - Go to Docker Desktop > Settings > Resources > File Sharing")
    print("   - Ensure your project directory is in the allowed list")
    
    print("\n3. Try setting explicit Docker host in .env")
    print("   - Add: DOCKER_HOST=unix:///var/run/docker.sock")
    print("   - Or:  DOCKER_HOST=tcp://localhost:2375 (if exposed)")
    
    print("\n4. For macOS Docker Desktop socket access:")
    print("""
    # Add to docker-compose.yml under api > environment:
    - DOCKER_HOST=${DOCKER_HOST:-unix:///var/run/docker.sock}
    
    # And mount the socket:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    """)
    
    print("\n5. Verify Docker Desktop settings")
    print("   - Go to Docker Desktop > Settings > General")
    print("   - Check 'Expose daemon on tcp://localhost:2375 without TLS'")
    print("   - Restart Docker Desktop")

def main():
    """Main entry point."""
    print_header("Docker Connection Test for macOS")
    
    cli_works = test_docker_cli()
    socket_works = test_docker_socket()
    test_environment()
    
    if cli_works and socket_works:
        print_header("RESULT: All Docker connections working! 🎉")
    else:
        print_header("RESULT: Some Docker connections failed 😕")
        suggest_fixes()
    
    return 0 if cli_works and socket_works else 1

if __name__ == "__main__":
    sys.exit(main())