import json
import re
from typing import Tuple
from urllib.parse import urljoin, urlsplit

import requests
from lxml import html
from lxml.etree import LxmlError
from requests.exceptions import HTTPError, RequestException

# Sources of inspiration
# https://stackoverflow.com/a/7160778/8065825
# https://stackoverflow.com/a/55827638/8065825
URL_PATTERN = re.compile(
    # accept only "http" and "https" as per Exercise 1 requirement
    r"(?:^https?://)"
    # http basic authentication [optional]
    r"(?:(\w{1,255}):(.{1,255})@)?"
    # check full domain length to be less than or equal to 253 (starting after
    # http basic auth, stopping before port)
    r"(?:(?:(?=\S{0,253}(?:$|:))"
    # check for at least one subdomain (maximum length per subdomain: 63
    # characters), dashes in between allowed
    r"((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    # check for top level domain, no dashes allowed
    r"(?:[a-z0-9]{1,63})))"
    # accept also "localhost" only
    r"|localhost)"
    # port [optional]
    r"(:\d{1,5})?"
    # trailing slash and URL parameters [optional]
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def _is_valid_url(user_input: str) -> bool:
    """Determine if the given user input is a valid URL.

    Notes:
        Checks only if the URL is not malformed, not if it is reachable.

    Args:
        user_input (str): The given user input.

    Returns:
        bool: `True` if the user input is a valid URL, `False` otherwise.
    """
    return re.match(URL_PATTERN, user_input) is not None


class Worker:

    def _get_valid_user_url(self) -> bool:
        """Prompt user for input; store URL and its components if valid.

        Returns:
            bool: `True` if the user input is a valid URL, `False` otherwise.
        """
        user_input = input("\nPlease enter your URL:\n").strip()

        if _is_valid_url(user_input):
            self.url = user_input
            self.url_components = urlsplit(user_input)
            return True

        return False

    def _get_page_source(self) -> bool:
        """Retrieve the page source from the user URL.

        Returns:
            bool: `True` if successful, `False` otherwise.
        """
        try:
            response = requests.get(self.url)
            response.raise_for_status()
        except HTTPError or RequestException:
            return False

        if 'text/html' in response.headers['content-type']:
            self.page_source = response.content
            return True

        return False

    def _parse_page_source(self) -> bool:
        """Parse the page source, and retrieve and store the required data.

        Returns:
            bool: `True` if successful, `False` otherwise.
        """
        try:
            root = html.fromstring(self.page_source)
        except LxmlError:
            return False

        title = root.xpath("./head/title")
        self.title = title[0].text if len(title) else ""

        # While stylesheets are generally loaded in `<head>`, they may also be
        # found in `<body>`.
        self.stylesheets = len(root.xpath(".//link[@rel='stylesheet']"))

        self.image_urls = root.xpath("./body//img/@src")
        self.images = len(self.image_urls)

        return True

    def _ensure_img_abs_urls(self) -> None:
        """Ensure that all image URLs are absolute.
        For relative image URLs, add the missing components from the page URL.
        """
        for i in range(self.images):
            components = urlsplit(self.image_urls[i])
            if not (components.scheme and components.netloc):
                self.image_urls[i] = urljoin(self.url, self.image_urls[i])

    def _generate_output(self) -> None:
        """Generate and store the output dict.
        """
        self.output = {
            "domain_name": self.url_components.netloc,
            "protocol": self.url_components.scheme,
            "title": self.title,
            "image": self.image_urls,
            "stylesheets": self.stylesheets,
        }

    def do_work(self) -> Tuple[str, int]:
        """Retrieve and return the data requested in the requirements or error.

        Returns:
            tuple:
                str: The formatted output data or an error message.
                int: The program exit code: 0 if successful, 1 if unsuccessful.
        """
        if not self._get_valid_user_url():
            return "Sorry, you entered an invalid or unsupported URL.", 1

        if not (self._get_page_source() and self._parse_page_source()):
            return f"Sorry, your URL does not link to a valid HTML page.", 1

        self._ensure_img_abs_urls()

        self._generate_output()

        return json.dumps(self.output, indent=2), 0


def main():
    """Instantiate and run the worker. Print the output data or error.
    """
    worker = Worker()
    output, status = worker.do_work()

    print(f"\n{output}\n")
    exit(status)


if __name__ == "__main__":
    main()
