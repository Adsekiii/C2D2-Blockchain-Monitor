import asyncio
from blocks_monitor import monitor_blocks

def main():
    try:
        asyncio.run(monitor_blocks())
    except KeyboardInterrupt:
        print("\nUżytkownik wstrzymał działanie")


if __name__ == "__main__":
    main()