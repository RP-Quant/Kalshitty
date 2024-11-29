import asyncio
class WorkerManager:
    semaphore = asyncio.Semaphore(2)  # Limit to 2 concurrent workers

    def __init__(self, name):
        self.name = name

    async def step_one(self):
        async with WorkerManager.semaphore:
            print(f"{self.name} is performing step one...")
            await asyncio.sleep(1)
            print(f"{self.name} finished step one.")

    async def step_two(self):
        async with WorkerManager.semaphore:
            print(f"{self.name} is performing step two...")
            await asyncio.sleep(1)
            print(f"{self.name} finished step two.")

    async def run_all(self):
        await self.step_one()
        await self.step_two()

async def main():
    workers = [WorkerManager(f"Worker-{i}") for i in range(5)]
    tasks = [worker.run_all() for worker in workers]
    await asyncio.gather(*tasks)

asyncio.run(main())
