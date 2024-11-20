import asyncio
import aiohttp
import json
import time

class DataFetcherPoster:
    data_store = None  # Class variable to hold the most recent data
    data_timestamp = 0  # Timestamp to track data freshness
    mutex = asyncio.Lock()  # Class variable for an asyncio lock

    def __init__(self, post_url, get_urls, fetch_interval=0.15):
        self.post_url = post_url
        self.get_urls = get_urls
        self.fetch_interval = fetch_interval  # Interval in seconds between each dispatched GET request

    async def post_data(self, session):
        while True:
            await asyncio.sleep(3)  # Simulate delay between posts
            async with self.mutex:
                if self.data_store is not None:
                    # Post the most recent data from data_store
                    async with session.post(self.post_url, json=self.data_store) as response:
                        post_response = await response.json()
                        print("Posted data response:")
                        print(post_response)
                else:
                    print("No data available to post")

    async def fetch_data(self, session, url):
        while True:
            # Dispatch a GET request without waiting for the previous request to finish
            asyncio.create_task(self._fetch_and_update_data(session, url))
            await asyncio.sleep(self.fetch_interval)  # Wait before dispatching the next request

    async def _fetch_and_update_data(self, session, url):
        async with session.get(url) as response:
            data = await response.text()
            parsed_data = json.loads(data)
            current_time = time.time()  # Capture the current time when data is fetched

            # Locking the mutex to safely update class variables
            async with self.mutex:
                # Only update if the new data is more recent
                if current_time > self.data_timestamp:
                    self.data_store = {
                        "title": f"Reposted: {parsed_data['title']}",
                        "body": parsed_data['body'],
                        "userId": parsed_data['userId']
                    }
                    self.data_timestamp = current_time
                    print(f"Fetched and updated data from {url} (timestamp: {current_time})")

    async def run(self):
        async with aiohttp.ClientSession() as session:
            # Create tasks for continuous GET operations
            fetch_tasks = [self.fetch_data(session, url) for url in self.get_urls]

            # Create task for continuous POST operation
            post_task = self.post_data(session)

            # Run all tasks concurrently
            await asyncio.gather(*fetch_tasks, post_task)

def main():
    # URLs for POST and GET requests
    post_url = "https://jsonplaceholder.typicode.com/posts"
    get_urls = [
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://jsonplaceholder.typicode.com/posts/2",
        "https://jsonplaceholder.typicode.com/posts/3"
    ]

    # Create an instance of the class and run it
    fetcher_poster = DataFetcherPoster(post_url, get_urls)
    asyncio.run(fetcher_poster.run())

if __name__ == "__main__":
    main()