import os
import argparse
from typing import Optional

from orchestrator import build_graph


def generate_graph_png(output_path: str) -> str:
    """Generate a Mermaid PNG of the orchestrator graph and save it.

    Returns the absolute path to the saved PNG.
    """
    compiled = build_graph()
    graph = compiled.get_graph()

    # Ensure output directory exists
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output) or ".", exist_ok=True)

    # draw_mermaid_png returns bytes; also writes to output_file_path if provided
    png_bytes = graph.draw_mermaid_png(
        output_file_path=abs_output,
        background_color="white",
        padding=10,
    )

    # Fallback: if the file was not written for some reason, write returned bytes
    if png_bytes and not os.path.exists(abs_output):
        with open(abs_output, "wb") as f:
            f.write(png_bytes)

    return abs_output


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate Mermaid PNG for the orchestrator graph")
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join("runs", "graph.png"),
        help="Path to save the PNG (default: runs/graph.png)",
    )
    args = parser.parse_args(argv)

    out = generate_graph_png(args.output)
    print(f"Saved graph PNG to: {out}")


if __name__ == "__main__":
    main()


