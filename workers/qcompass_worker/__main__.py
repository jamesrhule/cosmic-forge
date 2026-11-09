"""``python -m qcompass_worker --classes cpu,gpu_small`` (P3-02)."""

import sys

from ucgle_f1.worker import main

if __name__ == "__main__":
    sys.exit(main())
