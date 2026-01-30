import sys
import os
import argparse
from workers.standard import run_worker

def main():
    parser = argparse.ArgumentParser(description="Edge Compute Service Worker")
    # Kept argument for backward compatibility but it does nothing now
    parser.add_argument("--type", choices=["standard", "rag"], default="standard", help="Type of worker to run (Deprecated, always runs standard)")
    args = parser.parse_args()

    # Always run standard worker
    run_worker()

if __name__ == "__main__":
    main()
