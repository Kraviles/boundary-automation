import time
import requests

def requests_with_retry(url, retries=3, backoff_factor=0.3, timeout=10, headers=None):
    """
    Make a GET request with retries and exponential backoff.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if 500 <= e.response.status_code < 600:
                sleep_time = backoff_factor * (2 ** attempt)
                print(f"Server error ({e.response.status_code}) for {url}. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                continue
            else:
                raise e
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                sleep_time = backoff_factor * (2 ** attempt)
                print(f"Request failed for {url}: {e}. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                raise e
    # This part is reached only if all retries fail
    raise requests.exceptions.RequestException(f"All {retries} retries failed for {url}")
