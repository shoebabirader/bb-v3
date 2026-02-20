"""Safe Streamlit launcher with error handling and diagnostics."""

import subprocess
import sys
import time
import socket

def check_port_available(port=8501):
    """Check if port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except OSError:
        return False

def find_available_port(start_port=8501, max_attempts=10):
    """Find an available port."""
    for port in range(start_port, start_port + max_attempts):
        if check_port_available(port):
            return port
    return None

def main():
    """Start Streamlit with error handling."""
    print("="*60)
    print("🚀 STARTING STREAMLIT DASHBOARD")
    print("="*60)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit is installed")
    except ImportError:
        print("❌ Streamlit is not installed")
        print("\nInstalling Streamlit...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit", "streamlit-autorefresh"])
        print("✅ Streamlit installed")
    
    # Check if streamlit_app.py exists
    import os
    if not os.path.exists('streamlit_app.py'):
        print("❌ streamlit_app.py not found")
        print("Please run this script from the project root directory")
        return 1
    
    print("✅ streamlit_app.py found")
    
    # Check port availability
    port = 8501
    if not check_port_available(port):
        print(f"⚠️  Port {port} is already in use")
        new_port = find_available_port(port + 1)
        if new_port:
            print(f"✅ Using alternative port: {new_port}")
            port = new_port
        else:
            print("❌ No available ports found")
            print("\nTo fix:")
            print("  1. Close any running Streamlit instances")
            print("  2. Or use: streamlit run streamlit_app.py --server.port 8502")
            return 1
    else:
        print(f"✅ Port {port} is available")
    
    # Start Streamlit
    print(f"\n🚀 Starting Streamlit on port {port}...")
    print(f"📊 Dashboard will be available at: http://localhost:{port}")
    print("\n" + "="*60)
    print("Press Ctrl+C to stop the dashboard")
    print("="*60 + "\n")
    
    try:
        # Start Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        process = subprocess.Popen(cmd)
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"\n✅ Dashboard is running at: http://localhost:{port}")
            print("\nTo stop: Press Ctrl+C or close this window\n")
            
            # Wait for process to complete
            process.wait()
        else:
            print("\n❌ Streamlit failed to start")
            print("Check the error messages above")
            return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopping dashboard...")
        process.terminate()
        process.wait()
        print("✅ Dashboard stopped")
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
