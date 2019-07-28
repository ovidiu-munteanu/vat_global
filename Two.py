# ASSUMPTIONS:
#   "Monthly exchange rate" means "monthly average exchange rate"
#   "Official ECB rate" means "latest daily average rate"

from time import gmtime, mktime, strftime
from urllib.parse import urljoin

import requests
from lxml import etree

BITCOIN_TICKER = "https://blockchain.info/ticker"

DATE_FORMAT = "%Y-%m-%d"

ECB_DATA_API = "https://sdw-wsrest.ecb.europa.eu/service/data/"
ECB_EXR_GBP_EUR = "EXR/{0}.GBP.EUR.SP00.A"
ECB_QUERY_PARAMS = "?startPeriod={0}&endPeriod={1}&detail=dataonly"

FREQUENCY_DAILY = "D"
FREQUENCY_MONTHLY = "M"

TEN_DAYS_SECONDS = 60 * 60 * 24 * 10


def _today() -> str:
    """Return today's date (UTC) formatted as YYYY-MM-DD.

    Examples:
        2019-07-28

    Returns:
        str: The formatted date.
    """
    return strftime(DATE_FORMAT, gmtime())


def _ten_days_ago() -> str:
    """Return the date (UTC) from 10 days ago formatted as YYYY-MM-DD.

    Examples:
         2019-07-18 (given today's date is 2019-07-28)

    Returns:
        str: The formatted date.
    """
    ten_days_ago = gmtime(mktime(gmtime()) - TEN_DAYS_SECONDS)

    return strftime(DATE_FORMAT, ten_days_ago)


def _last_month() -> str:
    """Return the last month (UTC) formatted as YYYY-MM.

    Examples:
        2019-06 (given current month is 2019-07)

    Returns:
        str: The formatted month.
    """
    time_now = gmtime()

    return (
        f"{time_now.tm_year}-{time_now.tm_mon - 1:02d}" if time_now.tm_mon > 1
        else f"{time_now.tm_year - 1}-12"
    )


def _get_ecb_data(frequency: str, start: str, end: str) -> bytes:
    """Retrieve the ECB exchange rate data based on the arguments provided.

    Args:
        frequency (str): The frequency of the exchange rate.

        start (str): The start date of the period for which the exchange rate
        should be retrieved.

        end (str): The end date of the period for which the exchange rate should
        be retrieved.

    Notes:
        See https://sdw-wsrest.ecb.europa.eu/help/ for further details.

    Returns:
        bytes: The requested data.
    """
    content = bytearray()

    query_url = urljoin(ECB_DATA_API, ECB_EXR_GBP_EUR.format(frequency))
    query_url = urljoin(query_url, ECB_QUERY_PARAMS.format(start, end))

    with requests.get(query_url) as response:
        response.raise_for_status()
        # The data we're requesting is relatively small so we can just read it
        # one chunk; to do that we'll set the chunk size to something bigger
        # than the data we're reading. Based on some trial and error, it looks
        # like 3 KBytes is the right number.
        for chunk in response.iter_content(chunk_size=1024 * 3):  # 3 KBytes
            content.extend(chunk)

    return bytes(content)


def _get_latest_ecb_rate(data: bytes) -> float:
    """Retrieve the latest exchange rate from the given ECB data.

    Notes:
        The exchange rates are provided in chronological order in the ECB data
        so we just pick the last value in the list.

    Args:
        data (bytes): The ECB data.

    Returns:
        float: The latest exchange rate retrieved from the ECB data.
    """
    root = etree.fromstring(data)
    values = root.xpath('.//generic:ObsValue/@value', namespaces=root.nsmap)
    last_value = len(values) - 1

    return float(values[last_value])


class Worker:

    def _get_btc_eur_15min(self) -> None:
        """Retrieve and store the 15min delayed BTC market price in EUR.
        """
        with requests.get(BITCOIN_TICKER) as response:
            response.raise_for_status()
            json_data = response.json()

        self.btc_eur_15min = json_data["EUR"]["15m"]

    def _get_eur_gbp_last_month(self) -> None:
        """Retrieve and store last month's EUR to GBP average rate.
        """
        last_month = _last_month()
        data = _get_ecb_data(FREQUENCY_MONTHLY, last_month, last_month)

        self.eur_gbp_last_month = _get_latest_ecb_rate(data)

    def _get_eur_gbp_last_daily(self) -> None:
        """Retrieve and store the latest daily EUR to GBP average rate.
        """
        data = _get_ecb_data(FREQUENCY_DAILY, _ten_days_ago(), _today())

        self.eur_gbp_last_day = _get_latest_ecb_rate(data)

    def _get_btc_gbp_15min(self) -> None:
        """Calculate the 15min delayed BTC market price in GBP.

        Notes: This is calculated from the 15min delayed BTC market price in EUR
        using the ECB official latest daily average rate from EUR to GBP.
        """
        self._get_eur_gbp_last_daily()

        self.btc_gbp_15min = self.btc_eur_15min * self.eur_gbp_last_day

    def do_work(self) -> None:
        """Retrieve and display the data requested in the requirements.
        """
        self._get_btc_eur_15min()
        print(
            f"1 BTC = {self.btc_eur_15min} EUR"
            f"\t\t(15min delayed market price)"
        )

        self._get_eur_gbp_last_month()
        print(
            f"1 EUR = {self.eur_gbp_last_month} GBP"
            f"\t(last month average rate)"
        )

        self._get_btc_gbp_15min()
        print(
            f"1 BTC = {self.btc_gbp_15min:.6f} GBP"
            f"\t(BTC 15min delayed market price; GBP latest daily average rate)"
        )


def main() -> None:
    """Instantiate and run the worker.
    """
    worker = Worker()
    worker.do_work()


if __name__ == "__main__":
    main()
