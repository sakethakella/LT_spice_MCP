from fastmcp import FastMCP
import os
from pathlib import Path
import subprocess
import numpy as np
from PyLTSpice import RawRead
import matplotlib.pyplot as plt
from fastmcp.utilities.types import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORAGE_DIR = PROJECT_ROOT / "storage"
DEFAULT_LTSPICE_PATH = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Programs"
    / "ADI"
    / "LTspice"
    / "LTspice.exe"
)

mcp = FastMCP("LTspice MCP")


def _storage_file(name: str) -> Path:
    """Return a file inside storage while rejecting path traversal."""
    candidate = (STORAGE_DIR / name).resolve()
    if candidate.parent != STORAGE_DIR.resolve():
        raise ValueError("File name must refer to a file directly inside storage")
    return candidate

@mcp.tool(
    name="run_simulation",
    title="Run LTspice Simulation",
    description="""
                Run an LTspice simulation from a complete SPICE netlist.

                Use this tool when a circuit netlist has been generated and needs to be
                simulated using the locally installed LTspice application.

                The tool saves the supplied netlist string as a .net file, executes LTspice
                in batch mode, and collects the resulting .raw and .log files.

                The netlist should:
                - Be a complete LTspice-compatible SPICE netlist.
                - Preserve newline characters and SPICE line structure.
                - Contain all required circuit components, sources, models, and directives.
                - Include an appropriate analysis command such as .tran, .ac, .dc, or .op.
                - End with .end.

                The .raw file contains numerical simulation waveform data and can be used by
                other tools for waveform analysis and plotting.

                The .log file contains LTspice simulation messages and may contain .meas
                measurement results.

                Call this tool only after a valid netlist has been constructed.
                """,
     tags={
        "ltspice",
        "circuit-simulation",
        "electronics",
        "spice",
        "vlsi"
    },
    meta={
        "application": "LTspice",
        "domain": "electronic_design_automation",
        "tool_version": "1.0.0",
        "input_format": "SPICE_NETLIST",
        "simulation_engine": "LTspice",
        "output_artifacts": [
            "netlist",
            "raw",
            "log"
        ],
        "supported_analysis": [
            "transient",
            "AC",
            "DC",
            "operating_point",
            "noise"
        ]
    },
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
def run_simulation(file_name:str, net_file:str)->str:
    """
    Execute an LTspice simulation using a supplied SPICE netlist.

    Args:
        file_name:
            Name of the netlist file to create, for example "amplifier.net".

        net_file:
            Complete LTspice/SPICE netlist as a string. Newline characters
            must be preserved exactly because SPICE syntax is line-based.
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        file_path = _storage_file(file_name)
    except ValueError as error:
        return f"Error occurred while writing to file: {error}"

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(net_file)

    except Exception as e:
        return f"Error occurred while writing to file: {e}"
    
    ltspice_executable = Path(os.environ.get("LTSPICE_PATH", DEFAULT_LTSPICE_PATH))
    if not ltspice_executable.is_file():
        return (
            f"Error: LTspice executable was not found at {ltspice_executable}. "
            "Set LTSPICE_PATH to the full path of LTspice.exe."
        )
    cmd = [str(ltspice_executable), "-b", str(file_path)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        log_path = file_path.with_suffix(".log")
        log_content = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as log_file:
                log_content = log_file.read()
                
        return f"Simulation completed successfully.\n\nLog output:\n{log_content}"
        
    except subprocess.CalledProcessError as e:
        return f"LTspice execution failed with exit code {e.returncode}.\nStderr: {e.stderr}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

@mcp.tool(
        name="list_traces",
        description="""
        List all traces available in an LTspice .raw simulation result.

        Use this tool after run_simulation when you need to know which
        voltages or currents can be plotted or analyzed.

        Args:
            filename:
                Base name of the LTspice RAW file, without the .raw extension.
                For example, 'amplifier' refers to '../storage/amplifier.raw'.

        Returns:
            A list of trace names available in the RAW file.
            Examples include 'time', 'V(in)', 'V(out)', and 'I(R1)'.
        """
)
def list_traces(filename:str)->list:
    raw_path = _storage_file(f"{filename}.raw")

    if not raw_path.exists():
        raise FileNotFoundError(
            f"LTspice RAW file not found: {raw_path}"
        )

    rawfile = RawRead(raw_path)
    return rawfile.get_trace_names()

@mcp.tool(
        name="provide_plots",
        description="""
                Generate a PNG plot from an LTspice .raw simulation result.
                Use this tool after run_simulation to visualize simulation data.
                Args:
                    filename:
                        Base name of the LTspice RAW file, without the .raw extension.
                    trace_name1:
                        Name of the LTspice trace to place on the Y-axis.
                        Examples: V(out), V(in), I(R1).
                    trace_name2:
                        Name of the LTspice trace to place on the X-axis.
                        Examples: time, V(in), V(out).
                The x_trace and y_trace must exist in the same RAW file and contain
                compatible numbers of data points.
                Returns:
                    A PNG image containing the requested plot.
                """
)
def provide_plots(filename:str,trace_name1:str,trace_name2:str)->Image:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = _storage_file(f"{filename}.raw")
    png_path = _storage_file(f"{filename}_{trace_name1.replace('/', '_')}.png")

    if not raw_path.exists():
        raise FileNotFoundError(
            f"LTspice RAW file not found: {raw_path}"
        )

    rawfile = RawRead(raw_path)

    # Check requested trace
    available_traces = rawfile.get_trace_names()

    if trace_name1 not in available_traces:
        raise ValueError(
            f"Trace '{trace_name1}' not found. "
            f"Available traces: {available_traces}"
        )
    if trace_name2 not in available_traces:
        raise ValueError(
            f"Trace '{trace_name2}' not found. "
            f"Available traces: {available_traces}"
        )

    # Get traces
    y = rawfile.get_trace(trace_name1)
    x = rawfile.get_trace(trace_name2)

    steps = rawfile.get_steps()

    # Create a fresh figure for every tool call
    fig, ax = plt.subplots(figsize=(10, 6))

    for step_index, step_value in enumerate(steps):
        x_values = x.get_wave(step_index)
        y_values = y.get_wave(step_index)

        # AC analysis traces are complex; plot their magnitude on a log axis.
        if np.iscomplexobj(y_values):
            y_values = np.abs(y_values)
            ax.set_yscale("log")
            ax.set_xscale("log")

        ax.plot(
            x_values,
            y_values,
            label=str(step_value)
        )

    ax.set_xlabel(trace_name2)
    ax.set_ylabel(trace_name1)
    ax.set_title(f"LTspice: {trace_name1} vs {trace_name2}")
    ax.grid(True)
    # Only show legend when there are multiple steps
    if len(steps) > 1:
        ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return Image(path=png_path)

@mcp.tool(
    name="create_schematic_file",
    title="Create LTspice Schematic File",
    description="""
        Create an LTspice .asc schematic file from validated schematic content.

        Use this tool only after the corresponding circuit netlist has been
        successfully validated and, preferably, simulated.

        The content argument must contain complete LTspice schematic (.asc) text
        including component definitions, wire definitions, text directives, and
        other required schematic metadata.

        The generated file can be opened in LTspice as a graphical schematic,
        allowing the user to inspect, edit, and continue working on the circuit.

        IMPORTANT:
        - The schematic content must describe the same circuit that was verified
        in the corresponding SPICE netlist.
        - Do not invent or modify circuit connectivity when converting a verified
        netlist into a schematic.
        - Preserve line breaks and the exact schematic syntax supplied.
        - The filename should be a valid LTspice schematic filename.
        - This tool creates the schematic file; it does not run the simulation.

        Returns:
            The path of the successfully created .asc file.
            If file creation fails, an error message is returned.
            """,
    tags={
        "ltspice",
        "schematic",
        "electronics",
        "vlsi",
        "circuit-design",
    },
    meta={
        "application": "LTspice",
        "domain": "electronic_design_automation",
        "artifact_type": "schematic",
        "file_extension": ".asc",
        "workflow_stage": "post_simulation",
        "editable_by_user": True,
        "simulation_engine": "LTspice",
    },
)
def create_schematic_file(filename: str,content: str) -> str:
    schematic_name = Path(filename).name
    if Path(schematic_name).suffix.lower() == ".asc":
        schematic_name = Path(schematic_name).stem + ".asc"
    else:
        schematic_name = f"{schematic_name}.asc"

    if not schematic_name or schematic_name == ".asc":
        return "Error creating LTspice schematic: filename must not be empty."

    if not content.lstrip().startswith("Version 4"):
        return (
            "Error creating LTspice schematic: content must be a complete LTspice "
            "schematic beginning with 'Version 4'."
        )

    if "SHEET " not in content or not any(
        line.startswith("SYMBOL ") for line in content.splitlines()
    ):
        return (
            "Error creating LTspice schematic: content must include a SHEET line "
            "and at least one SYMBOL definition."
        )

    try:
        schematic_path = _storage_file(schematic_name)
    except ValueError as error:
        return f"Error creating LTspice schematic: {error}"

    try:
        with open(schematic_path, "w", encoding="utf-8") as f:
            f.write(content)

    except Exception as e:
        return f"Error creating LTspice schematic: {str(e)}"
    finally:
        if not os.path.exists(schematic_path):
            return f"Error: Failed to create LTspice schematic at {schematic_path}."
    return f"LTspice schematic created successfully at {schematic_path}"

if __name__ == "__main__":
    mcp.run()