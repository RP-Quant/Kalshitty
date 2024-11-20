import time
import requests

class SequentialDataFetcherPoster:
    data_store = None  # Class variable to hold the most recent data
    data_timestamp = 0  # Timestamp to track data freshness

    def __init__(self, post_url, get_urls, fetch_interval=0, post_interval=0):
        self.post_url = post_url
        self.get_urls = get_urls
        self.fetch_interval = fetch_interval  # Interval in seconds between each GET request
        self.post_interval = post_interval  # Interval in seconds between POST requests

    def fetch_data(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            current_time = time.time()  # Capture the current time when data is fetched

            # Update data_store only if the new data is more recent
            if current_time > self.data_timestamp:
                self.data_store = {
                    "title": f"Reposted: {data['title']}",
                    "body": data['body'],
                    "userId": data['userId']
                }
                self.data_timestamp = current_time
                print(f"Fetched and updated data from {url} (timestamp: {current_time})")
        else:
            print(f"Failed to fetch data from {url}, status code: {response.status_code}")

    def post_data(self):
        if self.data_store is not None:
            response = requests.post(self.post_url, json=self.data_store)
            if response.status_code == 201:
                print("Posted data response:")
                print(response.json())
            else:
                print(f"Failed to post data, status code: {response.status_code}")
        else:
            print("No data available to post")

    def run(self):
        while True:
            # Sequentially fetch data from each URL
            for url in self.get_urls:
                self.fetch_data(url)
                time.sleep(self.fetch_interval)  # Wait before the next fetch

            # Post data after fetching from all URLs
            self.post_data()
            time.sleep(self.post_interval)  # Wait before the next post cycle

# URLs for POST and GET requests
post_url = "https://jsonplaceholder.typicode.com/posts"
get_urls = [
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://jsonplaceholder.typicode.com/posts/2",
    "https://jsonplaceholder.typicode.com/posts/3"
]

# Create an instance of the class and run it
fetcher_poster = SequentialDataFetcherPoster(post_url, get_urls)
fetcher_poster.run()
