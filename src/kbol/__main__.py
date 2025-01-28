# src/kbol/__main__.py

import warnings
from cryptography.utils import CryptographyDeprecationWarning

# Filter out specific warnings
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*ARC4 has been moved.*")

from .cli.app import init_app

app = init_app()

def main():
    app()

if __name__ == "__main__":
    main()
