"""Entry point for the organize video package.

This module provides the command-line entry point for the video organization tool.
Run with: python -m organize

Note: This is a transitional module that delegates to the original organize.py
main function while the modular refactoring is completed.
"""

import sys
from pathlib import Path


def main() -> int:
    """
    Main entry point for the video organization tool.

    Delegates to the original organize.py main function for full functionality.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Import and run the original main function from organize.py
    # This ensures full functionality while the modular structure is in place
    organize_py = Path(__file__).parent.parent / "organize.py"

    if organize_py.exists():
        # Add parent directory to path for imports
        sys.path.insert(0, str(organize_py.parent))

        # Import the original module
        import importlib.util
        spec = importlib.util.spec_from_file_location("organize_original", organize_py)
        organize_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(organize_module)

        # Run the original main function
        organize_module.main()
        return 0
    else:
        print(f"Error: organize.py not found at {organize_py}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
