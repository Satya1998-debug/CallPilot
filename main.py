"""
CallPilot - Main Entry Point
Run this file to execute the appointment booking agent
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from callpilot.run import main

if __name__ == "__main__":
    # export = "--graph" in sys.argv
    export = True
    use_speech = "--speech" in sys.argv
    main(export_png=export, use_speech=use_speech)
