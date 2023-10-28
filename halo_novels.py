"""This programm gets all the halo novels from Halopedia."""

import base64
import datetime
import json
import logging
import random
import re
import time

import bs4
import requests


FORMATTER = logging.Formatter(fmt="[{asctime}] - {levelname:>8}: {message}",
                              datefmt="%Y-%m-%dT%H:%M:%S", style="{")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 "
    "Safari/537.36"
]  # WHY? I'm not making that many requests
JPG_MAGIC_NUMBER = b"\xff\xd8\xff"
PNG_MAGIC_NUMBER = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"

# - get all tables (series) /in main
# - get all novel links and basic info /in main
# - get more information (date for now) /in get_novel_information
# - get image /in get_novel_image


def get_novel_information(url: str) -> list[str]:
    page = requests.get(url, timeout=10,
                        headers={"User-Agent": random.choice(USER_AGENTS)})
    soup = bs4.BeautifulSoup(page.content, "html.parser")
    label = [label for label in soup.find_all("td", class_="infoboxlabel")
             if label.text.strip() == "Publication date:"][0]
    date_string = re.sub(r"\[\d\]", "", label.find_next(
        "td", class_="infoboxcell").text.split(" (")[0].strip())
    date = datetime.date.fromtimestamp(datetime.datetime.strptime(
        date_string, "%B %d, %Y").timestamp()).isoformat()
    return [date]


def get_novel_image(url: str) -> str:
    """Downloads the image at the url after . Also gets the real url.

    Arguments:
        - url: the url of the image.

    Returns:
        The image as a base64 encoded string or empty string if failed.
    """
    image = b""
    retries = 0
    url = url.replace("/thumb", "")
    # aaaaaaaaaaaahhh!
    if ".png" in url:
        url = url.split("png")[0] + "png"
        magic_number = PNG_MAGIC_NUMBER
    elif ".jpg" in url:
        url = url.split("jpg")[0] + "jpg"
        magic_number = JPG_MAGIC_NUMBER
    elif ".JPG" in url:
        url = url.split("JPG")[0] + "JPG"
        magic_number = JPG_MAGIC_NUMBER
    elif ".jpeg" in url:
        url = url.split("jpeg")[0] + "jpeg"
        magic_number = JPG_MAGIC_NUMBER
    else:
        return ""
    while not image.startswith(magic_number) and retries < 10:
        image = requests.get(url, timeout=10,
                             headers={"User-Agent": random.choice(USER_AGENTS)}).content
        retries += 1
    if image.startswith(magic_number):
        image_string = base64.b64encode(image).decode("utf-8")
    else:
        image_string = ""
    return image_string


def main() -> None:
    """The main method. Exists only for parity with comics.py."""
    # file_handler for logging
    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_handler = logging.FileHandler(filename=f"logs/halo_novels-{date}.log",
                                       mode="w", encoding="utf-8")
    file_handler.setFormatter(FORMATTER)
    file_handler.setLevel(logging.DEBUG)

    # console_handler for logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)
    console_handler.setLevel(logging.INFO)

    # logging setup
    logger = logging.getLogger("comics")
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # get novel page
    start_time = time.time()
    page = requests.get("https://www.halopedia.org/Halo_novels",
                        timeout=10, headers={"User-Agent": random.choice(USER_AGENTS)})
    logger.info("Got novels page in %s seconds.",
                round(time.time() - start_time, 2))

    novels_data = []
    soup = bs4.BeautifulSoup(page.content, "html.parser")
    for series_table in soup.find_all("table", class_="wikitable"):
        rows = series_table.find("tbody").find_all("tr")
        table_headers = [table_header.text.strip()
                         for table_header in rows[0].find_all("th")] + ["Series"]
        for novel in rows[1:]:
            novel_data = [table_data_cell.text.strip() if not table_data_cell.find("img")
                          else table_data_cell.find("img")["src"]
                          for table_data_cell in novel.find_all("td")] \
                + [series_table.find_previous("span", class_="mw-headline").text.strip()]
            date = get_novel_information(
                f"https://www.halopedia.org/{novel_data[0].replace(' ', '_')}")[0]
            novel_data[1] = get_novel_image(novel_data[1])
            novel_data[2] = re.split(", and |, ", novel_data[2])
            novel_data[3] = re.split(", and |, ", novel_data[3])
            novel_data[4] = date
            novels_data.append(dict(zip(table_headers, novel_data)))

    novels = {"_default": {str(index): novel
                           for index, novel in enumerate(novels_data)}}
    with open("halo_novels.json", "w", encoding="utf-8") as file:
        json.dump(novels, file)


if __name__ == "__main__":
    main()
