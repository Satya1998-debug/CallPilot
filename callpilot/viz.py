from __future__ import annotations
from pathlib import Path

def save_graph_png(app, out_path: str | Path = "artifacts/single_call_graph.png") -> str:
    """
    Save the compiled LangGraph as a PNG using Graphviz via pydot.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # LangGraph compiled graph exposes a graph representation you can draw.
    # This will work if graphviz + pydot are installed.
    g = app.get_graph()

    # Prefer PNG if available
    png_bytes = g.draw_png()
    out_path.write_bytes(png_bytes)

    return str(out_path)
