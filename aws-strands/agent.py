import argparse
import os
import sys
from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.vended_tools import file_editor, shell, http_request, web_fetch


def parse_arguments() -> tuple[str, str, str | None, str | None]:
    """Parse command-line arguments.

    Supports:
    - `-p` / `--prompt` OR a fallback positional argument for prompt text.
    - `-w` / `--working-folder` (defaults to current directory).
    - `-i` / `--input-folder` (optional read-only path).
    - `-o` / `--output-folder` (optional read/write output path; defaults to working folder).
    """
    parser = argparse.ArgumentParser(
        description="Strands Agent with folder context awareness."
    )

    # Flagged arguments
    parser.add_argument(
        "-p", "--prompt", type=str, help="Prompt text to pass to the agent"
    )
    parser.add_argument(
        "-w",
        "--working-folder",
        type=str,
        default=".",
        help="Path to the read/write working directory (default: current directory)",
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        default=None,
        help="Path to the read-only input directory",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=str,
        default=None,
        help="Path to the read/write output directory (default: working folder)",
    )

    # Fallback positional argument if -p flag is omitted
    parser.add_argument(
        "positional_prompt",
        nargs="?",
        type=str,
        help="Prompt text (if -p is omitted)",
    )

    args = parser.parse_args()

    # Fallback resolution logic: prioritize -p, then positional prompt
    prompt = args.prompt or args.positional_prompt
    if not prompt:
        parser.error(
            "A prompt must be supplied either via the -p flag or as a positional argument."
        )

    return prompt, args.working_folder, args.input_folder, args.output_folder


def validate_and_resolve_paths(
    working_folder: str, input_folder: str | None, output_folder: str | None
) -> tuple[str, str | None, str]:
    """Validate existence and access permissions for working, input, and output directories."""
    # Resolve working folder
    work_path = os.path.abspath(working_folder)
    if not os.path.exists(work_path):
        raise FileNotFoundError(f"Working folder does not exist: {work_path}")
    if not os.access(work_path, os.R_OK | os.W_OK):
        raise PermissionError(
            f"Working folder requires both read and write access: {work_path}"
        )

    # Resolve input folder (optional)
    input_path = None
    if input_folder:
        input_path = os.path.abspath(input_folder)
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input folder does not exist: {input_path}")
        if not os.access(input_path, os.R_OK):
            raise PermissionError(
                f"Input folder requires read access: {input_path}"
            )

    # Resolve output folder (defaults to working folder)
    if output_folder:
        output_path = os.path.abspath(output_folder)
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output folder does not exist: {output_path}")
        if not os.access(output_path, os.R_OK | os.W_OK):
            raise PermissionError(
                f"Output folder requires both read and write access: {output_path}"
            )
    else:
        output_path = work_path

    return work_path, input_path, output_path


def build_system_prompt(work_path: str, input_path: str | None, output_path: str) -> str:
    """Construct system prompt informing the agent of file system boundaries."""
    input_str = input_path if input_path else "Not specified"

    return f"""You are an AI agent with file system context awareness.

Execution Environment:
- Working Folder (Read/Write): {work_path}
- Input Folder (Read-Only): {input_str}
- Output Folder (Read/Write): {output_path}

Operational Directives:
1. Working Folder ({work_path}): You have full read and write capabilities here. You may use this folder for temporary scripts or intermediate processing.
2. Input Folder ({input_str}): You have read-only access. You may analyze data from this directory, but MUST NOT attempt to write, modify, or delete files within it.
3. Output Folder ({output_path}): You have full read and write capabilities here. All generated output — including code, reports, summaries, and any other produced artifacts — MUST be saved into this folder.
   """


def main():
    prompt, working_folder, input_folder, output_folder = parse_arguments()

    try:
        work_path, input_path, output_path = validate_and_resolve_paths(
            working_folder, input_folder, output_folder
        )
    except (FileNotFoundError, PermissionError) as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    # System instruction configured with dynamic environment paths
    system_prompt = build_system_prompt(work_path, input_path, output_path)

    # Initialize model and agent with system context
    model = OpenAIModel(model_id="gpt-5.4-nano")
    agent = Agent(model=model, tools=[file_editor, shell, web_fetch], system_prompt=system_prompt)

    # Execute request
    response = agent(prompt)
    print(response)


if __name__ == "__main__":
    main()



