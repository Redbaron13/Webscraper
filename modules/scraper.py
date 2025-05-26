import requests_html.requests
from requests_html import HTMLSession
from logger import debug, error as log_error

# Constants for timeouts
REQUEST_TIMEOUT = 30  # For the overall HTTP GET request
RENDER_SLEEP = 3      # Time in seconds to wait for JavaScript to load after page fetch but before JS execution
RENDER_TIMEOUT = 40   # Maximum time in seconds for the response.html.render() call

def fetch_html(url: str, attempt_js_render: bool = True) -> str | None:
    """
    Fetches HTML content from a given URL.

    Args:
        url: The URL to fetch HTML from.
        attempt_js_render: If True, tries to render JavaScript on the page.

    Returns:
        The HTML content as a string, or None if fetching fails.
    """
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        log_error(f"Invalid URL format: {url}")
        return None

    debug(f"Starting to fetch HTML for URL: {url}")
    session = HTMLSession()
    html_content_to_return = None

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)

        # Initial content is static HTML
        if response.html:
            html_content_to_return = response.html.html
        elif response.text: # Fallback if .html is None but .text is available
             html_content_to_return = response.text

        if attempt_js_render:
            debug(f"Attempting JavaScript rendering for {url} (sleep: {RENDER_SLEEP}s, timeout: {RENDER_TIMEOUT}s)")
            try:
                if response.html:
                    response.html.render(sleep=RENDER_SLEEP, timeout=RENDER_TIMEOUT)
                    # Update content with JS-rendered HTML
                    html_content_to_return = response.html.html
                    debug(f"JavaScript rendering completed for {url}")
                else:
                    log_error(f"Cannot render JavaScript for {url}: response.html is None. Static HTML will be used if available.")
            except requests_html.requests.exceptions.Timeout:
                log_error(f"JavaScript rendering timed out for {url} after {RENDER_TIMEOUT}s. Static HTML will be used if available.")
            except Exception as e:
                log_error(f"An error occurred during JavaScript rendering for {url}. Static HTML will be used if available.", error_obj=e)
        
        # Final check for content
        if not html_content_to_return and response.text:
            debug(f"HTML content was empty after potential rendering, falling back to response.text for {url}")
            html_content_to_return = response.text

        if not html_content_to_return:
            log_error(f"No HTML content could be retrieved for {url} (even after fallbacks).")
            return None

        debug(f"Successfully fetched HTML for {url}. Content length: {len(html_content_to_return)} bytes.")
        return html_content_to_return

    except requests_html.requests.exceptions.Timeout as e: # Specific exception for session.get() timeout
        log_error(f"Request timed out for {url} after {REQUEST_TIMEOUT}s (initial GET request).", error_obj=e)
        return None
    except requests_html.requests.exceptions.HTTPError as e:
        log_error(f"HTTP error occurred for {url}: {e.response.status_code}", error_obj=e)
        return None
    except requests_html.requests.exceptions.RequestException as e: # Catch other request-related exceptions
        log_error(f"A request exception occurred for {url}", error_obj=e)
        return None
    except Exception as e:
        log_error(f"An unexpected error occurred while fetching {url}", error_obj=e)
        return None
    finally:
        if session: # Ensure session is defined before trying to close
            session.close()
            debug(f"HTMLSession closed for {url}")

if __name__ == '__main__':
    # Testing for this module should be conducted via main.py or a dedicated test script.
    # This ensures that the project context (e.g., logger initialization) is correctly set up.
    pass
# End of modules/scraper.py