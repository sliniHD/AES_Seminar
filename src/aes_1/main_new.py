# main.py
import asyncio
from task_handler import handle_task


async def main():
    for i in range(1, 301):
        await handle_task(i)


if __name__ == "__main__":
    asyncio.run(main())
