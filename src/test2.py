import asyncio

async def my_async_function():
    await asyncio.sleep(1)  # Simulate some asynchronous work
    return "Hello, world!"

async def main():
    # Create a task
    task = asyncio.create_task(my_async_function())
    task1 = asyncio.create_task(my_async_function())
    task2 = asyncio.create_task(my_async_function())
    
    # Perform other work while the task runs
    print("Doing other work...")
    
    # Wait for the task to complete and get its result
    result = await task
    r2 = await task1
    r3 = await task2
    print("Task result:", result, r2, r3)

# Run the main coroutine
asyncio.run(main())
