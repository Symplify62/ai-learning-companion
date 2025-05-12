"""
Core utility functions for the application.
"""
import re
from urllib.parse import urlparse, urlunparse

def normalize_bilibili_url(url_string: str) -> str:
    """
    Normalizes a Bilibili video URL to a cleaner, canonical version.

    Aims to:
    1. Identify and extract the core video identifier (e.g., BV ID).
    2. Reconstruct a canonical URL, preferably `https://www.bilibili.com/video/BV.../`.
    3. Remove common tracking query parameters.
    4. Handle URLs starting with `http://` by converting to `https://`.
    5. Handle `b23.tv` short URLs by cleaning them to `https://b23.tv/SHORTCODE`.
    6. Handles direct BV ID input.

    Args:
        url_string: The Bilibili video URL string to normalize.

    Returns:
        A normalized URL string, or an empty string if normalization fails
        or the URL is not recognized.
    """
    if not url_string:
        return ""

    # Handle direct BV ID input (case-sensitive)
    # Example: "BV17x411w7KC" -> "https://www.bilibili.com/video/BV17x411w7KC/"
    bv_id_direct_match = re.fullmatch(r"BV[1-9A-HJ-NP-Za-km-z]{10}", url_string.strip())
    if bv_id_direct_match:
        return f"https://www.bilibili.com/video/{bv_id_direct_match.group(0)}/"

    try:
        # Strip whitespace before parsing
        parsed_url = urlparse(url_string.strip())
    except ValueError:  # Catches issues like URLs with spaces if not stripped, etc.
        return ""

    scheme = 'https'  # Always normalize to https
    netloc = parsed_url.netloc.lower() # Normalize netloc to lowercase for comparison
    path = parsed_url.path

    # Handle b23.tv short URLs
    # Example: "https://b23.tv/UROhDRL?extra_param=123" -> "https://b23.tv/UROhDRL"
    if "b23.tv" == netloc:
        # Extract the short code part from the path, e.g., /UROhDRL from /UROhDRL?query
        short_code_match = re.match(r"/([^/?]+)", path)
        if short_code_match:
            cleaned_path = f"/{short_code_match.group(1)}"
            return urlunparse((scheme, netloc, cleaned_path, '', '', ''))
        else:
            # Malformed b23.tv URL path (e.g., just "b23.tv/" or "b23.tv")
            return ""

    # Handle www.bilibili.com URLs or other bilibili.com subdomains
    if "bilibili.com" in netloc:
        # Regex for BV ID: BV[1-9A-HJ-NP-Za-km-z]{10} (case-sensitive)
        # Search in the original full URL string to catch BV ID from path or query parameters.
        bv_match = re.search(r"(BV[1-9A-HJ-NP-Za-km-z]{10})", url_string)

        if bv_match:
            bv_id = bv_match.group(1)
            # Reconstruct canonical URL, ensure trailing slash
            # Standard netloc for videos is www.bilibili.com
            return f"https://www.bilibili.com/video/{bv_id}/"
        else:
            # If no BV ID, this normalizer doesn\'t support it (e.g. old 'av' links without BV)
            # or it's not a video link.
            return ""
            
    # If URL is not recognized as a Bilibili or b23.tv domain that we can process
    return ""

if __name__ == '__main__':
    # Test cases
    urls_to_test = [
        "https://www.bilibili.com/video/BV1et421M74L/?spm_id_from=333.337.search-card.all.click&vd_source=c6f3ce690a98f2baadbebe03035d0049",
        "http://www.bilibili.com/video/BV1GF411p722?p=2&spm_id_from=333.1007.0.0&vd_source=some_source",
        "www.bilibili.com/video/BV13L4y117sW",
        "https://bilibili.com/video/BV1bA411g7qM/",
        "BV17x411w7KC",
        "https://b23.tv/UROhDRL?extra_param=123",
        "http://b23.tv/UROhDRL",
        "b23.tv/XYZ789",
        "https://www.bilibili.com/watchlater/#/BV1sS4y1C72E/RL270", # Complex path
        "https://www.bilibili.com/list/list_373762900?first_id=930209021&oid=930209021&spm_id_from=333.1007.0.0", # Playlist link
        "https://space.bilibili.com/22253003/video", # User space link
        "",
        None, # Test None input
        "これはURLではありません",
        "https://example.com/video/BV1et421M74L/" # Non-bilibili domain
    ]
    expected_outputs = [
        "https://www.bilibili.com/video/BV1et421M74L/",
        "https://www.bilibili.com/video/BV1GF411p722/",
        "https://www.bilibili.com/video/BV13L4y117sW/", # Assuming urlparse handles no scheme
        "https://www.bilibili.com/video/BV1bA411g7qM/",
        "https://www.bilibili.com/video/BV17x411w7KC/",
        "https://b23.tv/UROhDRL",
        "https://b23.tv/UROhDRL",
        "https://b23.tv/XYZ789", # Assuming urlparse handles no scheme
        "https://www.bilibili.com/video/BV1sS4y1C72E/", # Extracts BV ID
        "", # Playlist link, no BV ID for a single video
        "", # User space link, no specific video BV ID
        "",
        "", # None input
        "", # Invalid URL
        ""  # Non-bilibili domain
    ]

    for i, url in enumerate(urls_to_test):
        normalized = normalize_bilibili_url(url)
        print(f"Original:  \'{str(url)}\'")
        print(f"Normalized: \'{normalized}\'")
        print(f"Expected:   \'{expected_outputs[i]}\'")
        if normalized == expected_outputs[i]:
            print("Result: PASSED")
        else:
            print(f"Result: FAILED (Expected \'{expected_outputs[i]}\' but got \'{normalized}\')")
        print("-" * 30)

    # Specific test for a URL that urlparse might struggle with if not for strip() or careful parsing
    tricky_url = "   https://www.bilibili.com/video/BV1Xy4y1v7Zz   "
    print(f"Original:  \'{tricky_url}\'")
    print(f"Normalized: \'{normalize_bilibili_url(tricky_url)}\'")
    print(f"Expected:   \'https://www.bilibili.com/video/BV1Xy4y1v7Zz/\'")
    if normalize_bilibili_url(tricky_url) == "https://www.bilibili.com/video/BV1Xy4y1v7Zz/":
        print("Result: PASSED")
    else:
        print("Result: FAILED")
    print("-" * 30)

    # Test case: URL with BV ID only in query params
    query_url = "https://www.bilibili.com/s/video/something?bvid=BV1qM4y1N72Z&other_param=test"
    print(f"Original:  \'{query_url}\'")
    print(f"Normalized: \'{normalize_bilibili_url(query_url)}\'")
    print(f"Expected:   \'https://www.bilibili.com/video/BV1qM4y1N72Z/\'")
    if normalize_bilibili_url(query_url) == "https://www.bilibili.com/video/BV1qM4y1N72Z/":
        print("Result: PASSED")
    else:
        print("Result: FAILED")
    print("-" * 30)

    # Test case for b23.tv without path
    b23_no_path = "https://b23.tv"
    print(f"Original:  \'{b23_no_path}\'")
    print(f"Normalized: \'{normalize_bilibili_url(b23_no_path)}\'")
    print(f"Expected:   \'\'")
    if normalize_bilibili_url(b23_no_path) == "":
        print("Result: PASSED")
    else:
        print("Result: FAILED")
    print("-" * 30)
    
    b23_just_slash = "https://b23.tv/"
    print(f"Original:  \'{b23_just_slash}\'")
    print(f"Normalized: \'{normalize_bilibili_url(b23_just_slash)}\'")
    print(f"Expected:   \'\'")
    if normalize_bilibili_url(b23_just_slash) == "":
        print("Result: PASSED")
    else:
        print("Result: FAILED")
    print("-" * 30) 