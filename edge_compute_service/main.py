import sys
import os
import argparse
from workers.standard import run_worker
from workers.rag_worker import run_rag_worker

def main():
    parser = argparse.ArgumentParser(description="Edge Compute Service Worker")
    parser.add_argument("--type", choices=["standard", "rag"], default="standard", help="Type of worker to run")
    args = parser.parse_args()

    # Also support ENV var
    worker_type = os.getenv("WORKER_TYPE", args.type)

    if worker_type == "rag":
        run_rag_worker()
    else:
        run_worker()

if __name__ == "__main__":
    main()
