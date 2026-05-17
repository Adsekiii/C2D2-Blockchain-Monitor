import sys

import gui


def main():
    try:
        gui.main()
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
