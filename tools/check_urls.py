import asyncio

import aiohttp
from javascript_data_files import read_js, write_js


async def check_url(session, url):
    try:
        timeout = aiohttp.ClientTimeout(total=10)

        # Try HEAD first
        async with session.head(url, timeout=timeout, allow_redirects=True) as response:
            # If HEAD returns client error, try GET
            if 400 <= response.status < 500:
                async with session.get(
                    url, timeout=timeout, allow_redirects=True
                ) as get_response:
                    return (get_response.status, None)
            return (response.status, None)

    except aiohttp.ClientError as e:
        # If HEAD fails with exception, try GET
        try:
            async with session.get(
                url, timeout=timeout, allow_redirects=True
            ) as response:
                return (response.status, None)
        except aiohttp.ClientError:
            return (None, str(e))
    except asyncio.TimeoutError:
        return (None, "Request timeout")


async def check_urls():
    """
    Checks all bookmark URLs for reachability and updates the description for those that fail.
    """
    from bookmarks.data.datafile import get_data_source

    data_source = get_data_source()
    bookmarks = read_js(data_source, varname="bookmarks")
    updated = False

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        tasks = []
        indices = []
        for i, bookmark in enumerate(bookmarks):
            if bookmark.get("url"):
                tasks.append(check_url(session, bookmark.get("url")))
                indices.append(i)

        results = await asyncio.gather(*tasks)
        for idx, (status, error) in zip(indices, results):
            if status and status >= 400:
                print(
                    f"FAIL: Entry {idx + 1}: {bookmarks[idx]['url']} - Status: {status}"
                )
                bookmarks[idx]["description"] = f"URL not reachable ({status})"
                updated = True
            elif error:
                error_message = error.split("\n")[0]  # Get a concise error message
                print(
                    f"FAIL: Entry {idx + 1}: {bookmarks[idx]['url']} - Error: {error_message}"
                )
                bookmarks[idx]["description"] = "URL not reachable (Connection Error)"
                updated = True

        if updated:
            print("\nWriting updated data back to bookmarks.js...")
            write_js(data_source, value=list(bookmarks), varname="bookmarks")
            print("Done.")
        else:
            print("No unreachable URLs found. Nothing to update.")


if __name__ == "__main__":
    asyncio.run(check_urls())
