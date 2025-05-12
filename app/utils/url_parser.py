import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def normalize_bilibili_url(raw_url: str) -> str:
    """
    Normalizes a Bilibili video URL to a clean version.

    Extracts the core video ID (BV or av) and preserves the 'p' query parameter.
    Removes other common tracking or unnecessary query parameters.

    Args:
        raw_url: The raw Bilibili video URL string.

    Returns:
        A cleaned Bilibili video URL string, or the original URL if parsing fails.
    """
    try:
        parsed_url = urlparse(raw_url)

        if not parsed_url.scheme or not parsed_url.netloc.endswith("bilibili.com"):
            # Not a valid Bilibili URL or not a domain we are targeting
            return raw_url

        path_parts = parsed_url.path.strip('/').split('/')
        video_id_part = None

        # Expected path structure: /video/BVxxxxxxxxxx or /video/avxxxxxxxx
        if len(path_parts) >= 2 and path_parts[0] == 'video':
            video_id_candidate = path_parts[1]
            # Regex to match BV or av IDs
            # BV IDs are typically 10 alphanumeric characters after 'BV1'
            # av IDs are 'av' followed by digits
            if re.match(r"^(BV[1-9A-HJ-NP-Za-km-z]{10})$", video_id_candidate) or \
               re.match(r"^(av\d+)$", video_id_candidate):
                video_id_part = video_id_candidate
        
        if not video_id_part:
            # Could not extract a valid video ID from the path
            return raw_url

        # Preserve 'p' query parameter if it exists
        query_params = parse_qs(parsed_url.query)
        preserved_params = {}
        if 'p' in query_params:
            preserved_params['p'] = query_params['p'][0] # Take the first value if multiple

        # Reconstruct the clean URL
        clean_path = f"/video/{video_id_part}/"
        clean_query = urlencode(preserved_params) if preserved_params else ""
        
        # Use https as the default scheme
        clean_url_parts = ('https', 'www.bilibili.com', clean_path, '', clean_query, '')
        return urlunparse(clean_url_parts)

    except Exception:
        # In case of any parsing error, return the original URL
        return raw_url

if __name__ == '__main__':
    # Test cases
    urls_to_test = [
        "https://www.bilibili.com/video/BV1BTQmYNE6f/?spm_id_from=333.337.search-card.all.click&vd_source=c6f3ce690a98f2baadbebe03035d0049",
        "http://www.bilibili.com/video/av12345678?p=2&t=120",
        "https://www.bilibili.com/video/BV1hK4y1L7kG?p=3&share_source=copy_web&share_medium=web&share_plat=web&share_session_id=xxxxxxxx&share_tag=s_i&timestamp=1678888888",
        "https://www.bilibili.com/video/BV1hK4y1L7kG/",
        "https://www.bilibili.com/video/av98765432",
        "https://m.bilibili.com/video/BV1BTQmYNE6f", # Mobile, should ideally redirect or be handled, but current logic focuses on www
        "https://www.bilibili.com/watchlater/#/BV1BTQmYNE6f/", # Watchlater URL, might not be parsed correctly by current logic
        "https://www.bilibili.com/medialist/play/12345/BV1BTQmYNE6f", # Medialist, might not be parsed correctly
        "invalid-url",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Non-Bilibili URL
    ]

    for url in urls_to_test:
        print(f"Original: {url}")
        print(f"Normalized: {normalize_bilibili_url(url)}\n")

    # Example with no query params
    print(f"Original: https://www.bilibili.com/video/BV1234567890/")
    print(f"Normalized: {normalize_bilibili_url('https://www.bilibili.com/video/BV1234567890/')}\n")

    # Example with only 'p' param
    print(f"Original: https://www.bilibili.com/video/BV1234567890/?p=5")
    print(f"Normalized: {normalize_bilibili_url('https://www.bilibili.com/video/BV1234567890/?p=5')}\n")

    # Example with other params that should be stripped
    print(f"Original: http://www.bilibili.com/video/av123/?t=100&spm=test")
    print(f"Normalized: {normalize_bilibili_url('http://www.bilibili.com/video/av123/?t=100&spm=test')}\n")