from fastmcp import FastMCP
import os
from pathlib import Path
import subprocess

mcp=FastMCP("my first MCP")

@mcp.tool
def run_simulation(file_name:str, net_file:str)->str:
    """Run an LTspice simulation using a provided netlist string.
    
    Args:
        file_name: The name of the netlist file to save (e.g., 'circuit.net').
        net_file: The raw netlist content as a string containing circuit components and analysis commands.make sure use tripple quotation marks so as to save the \n effect as .net files are senstitive to this 
        
    Returns:
        A string containing the simulation execution status and the contents of the generated .log file.
    """
    directory_path=Path("../storage")
    directory_path.mkdir(parents=True, exist_ok=True)
    file_path =os.path.join(directory_path, file_name)
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(net_file)

    except Exception as e:
        return f"Error occurred while writing to file: {e}"
    
    ltspice_executable = r"C:\Users\Saketh Akella\AppData\Local\Programs\ADI\LTspice\LTspice.exe"
    if not ltspice_executable or not os.path.exists(ltspice_executable):
        return (
            "Error: LTSPICE_PATH environment variable is not set or points to an invalid path. "
            "Please ensure LTSPICE_PATH is configured in your environment."
        )
    cmd = [ltspice_executable, "-b", str(file_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log_path = str(file_path).rsplit(".", 1)[0] + ".log"
        log_content = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as log_file:
                log_content = log_file.read()
                
        return f"Simulation completed successfully.\n\nLog output:\n{log_content}"
        
    except subprocess.CalledProcessError as e:
        return f"LTspice execution failed with exit code {e.returncode}.\nStderr: {e.stderr}"
    except Exception as e:
        return f"An error occurred: {str(e)}"


if __name__ == "__main__":
    mcp.run()