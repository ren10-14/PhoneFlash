"""
PhoneFlash PC — точка входа.
"""
import sys
from app import PhoneFlashApp


def main():
    app = PhoneFlashApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()