"""A csomag futtatható belépési pontja: python -m gdmodule"""

import sys

from gdmodule.cli import main

if __name__ == "__main__":
    sys.exit(main())
