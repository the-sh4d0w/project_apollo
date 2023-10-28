"""This programm gets all the comics from 'Checkliste DC-Comics' from
https://paninishop.de/checkliste/dc-comics/. The comics will be saved as JSON in 'comics.json'.
"""

import base64
import datetime
import inspect
import json
import logging
import multiprocessing
import random
import re
import time
import typing

import bs4
import requests
import rich.color
import rich.console
import rich.highlighter
import rich.live
import rich.logging
import rich.progress
import rich.theme


THEME = rich.theme.Theme({
    "log.datetime": rich.color.Color.from_rgb(44, 88, 172).name,
    "log.func_notset": rich.color.Color.from_rgb(128, 128, 128).name,
    "log.func_debug": rich.color.Color.from_rgb(0, 0, 255).name,
    "log.func_info": rich.color.Color.from_rgb(0, 255, 0).name,
    "log.func_warn": rich.color.Color.from_rgb(255, 255, 0).name,
    "log.func_error": rich.color.Color.from_rgb(255, 165, 0).name,
    "log.func_critical": rich.color.Color.from_rgb(255, 0, 0).name,
    "log.proc": rich.color.Color.from_rgb(25, 140, 162).name
})
FORMATTER = logging.Formatter(fmt="[{time}] [{func}/{levelname}] ({proc}) {message}",
                              datefmt="%Y-%m-%d %H:%M:%S", style="{")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/51.0.2704.103 Safari/537.36"
]


class LogHighlighter(rich.highlighter.RegexHighlighter):
    """Apply style to logs."""

    base_style = "log."
    highlights = [
        r"(?P<datetime>(\[-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-"
        r"(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])Z\])",
        r"(?P<func_notset>\[[a-zA-Z_]*\/NOTSET\])",
        r"(?P<func_debug>\[[a-zA-Z_]*\/DEBUG\])",
        r"(?P<func_info>\[[a-zA-Z_]*\/INFO\])",
        r"(?P<func_warn>\[[a-zA-Z_]*\/WARNING\])",
        r"(?P<func_error>\[[a-zA-Z_]*\/ERROR\])",
        r"(?P<func_critical>\[[a-zA-Z_]*\/CRITICAL\])",
        r"(?P<proc>\([a-zA-Z0-9\- ]*\))"
    ]


class Apollo:
    """Apollo class thing."""

    def __init__(self) -> None:
        """Initialize apollo.

        Returns:
            Nothing.
        """
        manager = multiprocessing.Manager()
        self.logger_queue = manager.Queue()

    def logger_thread(self) -> None:
        """Seperate for logging.

        Returns:
            Nothing.
        """
        try:
            # file_handler for logging
            date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_handler = logging.FileHandler(filename=f"logs/comics-{date}.log",
                                               mode="w", encoding="utf-8")
            file_handler.setFormatter(FORMATTER)
            file_handler.setLevel(logging.DEBUG)

            # console_handler for logging
            log_console = rich.console.Console(theme=THEME)
            console_handler = rich.logging.RichHandler(console=log_console, show_time=False,
                                                       show_level=False, show_path=False,
                                                       highlighter=LogHighlighter())
            console_handler.setFormatter(FORMATTER)
            console_handler.setLevel(logging.INFO)

            # logging setup
            logger = logging.getLogger("comics")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            # progress setup
            progress = rich.progress.Progress("{task.description}", rich.progress.SpinnerColumn(),
                                              rich.progress.BarColumn(), rich.progress.TextColumn(
                "[progress.percentage]{task.percentage:>3.0f}%"),
                rich.progress.TimeRemainingColumn(), rich.progress.TimeElapsedColumn())

            # log
            with rich.live.Live(progress, console=log_console):
                while True:
                    data = self.logger_queue.get()
                    # end logging process if data is False
                    if not data:
                        return
                    if len(data) == 2:
                        # this could be a problem, because it assumes that the total will
                        # be received before any logging from the corresponding functions
                        match data[0]:
                            case "links":
                                task_links = progress.add_task("Getting links...",
                                                               total=data[1])
                            case "info":
                                task_info = progress.add_task("Getting information...",
                                                              total=data[1])
                            case "image":
                                task_image = progress.add_task("Getting images...",
                                                               total=data[1])
                    else:
                        match data[2]["func"]:
                            case "get_comic_links":
                                progress.advance(task_links)
                            case "get_comic_information":
                                progress.advance(task_info)
                            case "get_comic_image":
                                progress.advance(task_image)
                        logger.log(level=data[0], msg=data[1], extra=data[2])
        except (KeyboardInterrupt, Exception) as excp:  # pylint: disable=broad-except
            now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            logger.critical(msg=f"{excp.__class__.__name__}: {excp}"
                            if len(str(excp)) > 0 else excp.__class__.__name__,
                            extra={"func": inspect.stack()[0][3],
                                   "proc": multiprocessing.current_process().name,
                                   "time": now})

    def log(self, level: int, msg: str, func_name: str = "") -> None:
        """Log a message. Gets sent to thread where it actually gets logged.

        Arguments:
            - level: level to log with.
            - msg: message to log.

        Returns:
            Nothing.
        """
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.logger_queue.put((level, msg, {"func": func_name
                                            if len(func_name) > 0 else inspect.stack()[1][3],
                                            "proc": multiprocessing.current_process().name,
                                            "time": now}))

    def poolmap(self, func: typing.Callable, iterable: list[typing.Any]) -> list[typing.Any]:
        """Map iterable to function and execute in multiple processes in a pool.
        Basically just wraps multiprocessing.Pool.imap with some error handling.

        Arguments:
            - func: function to apply.
            - iterable: arguments for function.

        Returns:
            The results.
        """
        # this function will not log correctly; func should be correct, but proc will be wrong
        result = []
        with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
            iterator = pool.imap(func, iterable)
            while True:
                try:
                    result.append(next(iterator))
                except StopIteration:
                    break
                except Exception as excp:  # pylint: disable=broad-except
                    self.log(logging.ERROR,
                             f"{excp.__class__.__name__}: {excp}",
                             func.__name__)
        return result

    def stories_to_list(self, stories: str) -> list[str]:
        """Gets all stories from text. Does some regex magic.

        Arguments:
            - stories: the (horribly formatted) stories as text.

        Returns.
            The stories in as list.
        """
        story_list = []
        comic_name = ""
        for item in stories.split(", "):
            if text := re.search(r"\d+(-|–)\d+", item):
                comic_name = re.sub(r"\d+(-|–)\d+", "", item)
                start, end = re.split(r"-|–", text.group())
                for number in range(int(start), int(end) + 1):
                    story_list.append(f"{comic_name}{number}")
                continue
            elif re.search(r"\w\s\d+(\s\([I]+\))?", item):
                comic_name = re.sub(r"\s\d+(\s\([I]+\))?", "", item)
            elif comic_name != "":
                item = f"{comic_name} {item}"
            story_list.append(item)
        return story_list

    def get_comic_links(self, page_number: int) -> list[str]:
        """Gets all the comic links from a page of the paninishop dc comics checklist.

        Arguments:
            - page_number: the number for the page.

        Returns:
            The links that were found.
        """
        respone = requests.get(
            f"https://paninishop.de/checkliste/dc-comics/?o=1&p={page_number}&n=100",
            timeout=10, headers={"User-Agent": random.choice(USER_AGENTS)})
        soup = bs4.BeautifulSoup(respone.content, "lxml")
        links = [link["href"].split("?")[0]
                 for link in soup.find_all("a", class_="product--title")]
        self.log(logging.DEBUG, f"Got {len(links)} comic links from "
                 f"page {page_number}.")
        return links

    def get_comic_information(self, url: str) -> dict:
        """Scrapes the url for information about a comic.
        Will only work with a paninishop comic site.

        Arguments:
            - url: the site with the comic.

        Returns:
            The information in a dictionary (in a list, doesn't work otherwise).
        """
        response = requests.get(url, timeout=10,
                                headers={"User-Agent": random.choice(USER_AGENTS)})
        soup = bs4.BeautifulSoup(response.content, "lxml")
        # basic information
        title = typing.cast(bs4.Tag, soup.find("h1", class_="product--title")
                            ).text.strip()
        image = typing.cast(bs4.Tag, soup.find("span", class_="image--element")
                            ).get("data-img-original")
        price = typing.cast(bs4.Tag, soup.find("meta", itemprop="price"))
        status = typing.cast(bs4.Tag, soup.find("span", class_="delivery--text")
                             ).text.strip()
        comic_information = {"Titel": title,
                             "Bildlink": image,
                             "Link": url,
                             "Preis": float(typing.cast(str, price.get("content")))
                             if price else None,
                             "Status": status}
        # more information
        for item in soup.find_all("li", class_="base-info--entry"):
            value = item.find("span").text.strip()
            match key := item.find("strong").text.strip():
                case "Artikel-Nr.:":  # rename key
                    comic_information.update({"Artikelnummer": value})
                case "Erscheint am:":  # as ISO 8601 format
                    comic_information.update({"Erscheinungsdatum":
                                              "-".join(value.split(".")[::-1])})
                case "Limitierte Auflage:":  # as list[int]
                    comic_information.update({"Limitierte Auflage":
                                              [int(number) for number in value.split(", ")]})
                case _:  # just normal str
                    comic_information.update(
                        {key.removesuffix(":"): value})
        # extra information in table
        for item in soup.find_all("tr", class_="product--properties-row"):
            value = item.find("td",
                              class_="product--properties-value").text.strip()
            match key := item.find("td", class_="product--properties-label").text.strip():
                # format information correctly as list[str]
                case "Storys:":
                    comic_information.update(
                        {"Storys": self.stories_to_list(value)})
                case "Zeichner:" | "Autor:" | "Charaktere:" | "Zielgruppe:" | "Genre:" \
                        | "Thema:" | "Marke:":  # as list[str]
                    comic_information.update({key.removesuffix(":"):
                                              value.split(", ")})
                case "Seitenzahl:":  # as int
                    comic_information.update({"Seitenzahl": int(value)})
                case "Serienstart:" | "Einsteigerfreundlich:":
                    comic_information.update({key.removesuffix(":"):
                                              value == "Ja"})
                case "Limitierte Auflage:":  # as list[int]
                    comic_information.update({"Limitierte Auflage":
                                              list(map(int, value.split(", ")))})
                case _:  # just normal str
                    comic_information.update(
                        {key.removesuffix(":"): value})
        self.log(logging.DEBUG, f"Got information about {comic_information['Titel']} "
                 f"from url {url}.")
        return comic_information

    def get_comic_image(self, url: str) -> str | None:
        """Downloads the image at the url.

        Arguments:
            - url: the url of the image.

        Returns:
            The image as a base64 encoded string or None if failed.
        """
        image = b""
        retries = 0
        while not image.startswith(b"\xff\xd8\xff") and retries < 10:
            image = requests.get(url, timeout=10, headers={
                "User-Agent": random.choice(USER_AGENTS)}).content
            retries += 1
        if image.startswith(b"\xff\xd8\xff"):
            image_string = base64.b64encode(image).decode("utf-8")
            self.log(logging.DEBUG, f"Got image from '{url}' with "
                     f"{retries} tries.")
        else:
            image_string = None
            self.log(logging.WARNING, f"Failed to get image from '{url}'.")
        return image_string

    def main(self) -> None:
        """It's just the main method. It's good practice, but, honestly, it only
        exists because multiprocessing doesn't work otherwise. For some reason.
        """
        try:
            # logging process setup
            log_proc = multiprocessing.Process(target=self.logger_thread,
                                               name="Logging")
            log_proc.start()

            # get the number of pages
            start_time = time.monotonic()
            page = requests.get("https://paninishop.de/checkliste/dc-comics/?o=1&n=100",
                                timeout=10, headers={"User-Agent": random.choice(USER_AGENTS)})
            soup = bs4.BeautifulSoup(page.content, "lxml")
            page_numbers = int(typing.cast(
                bs4.Tag, typing.cast(bs4.Tag, soup.find("span", class_="paging--display")
                                     ).find("strong")).text.strip())
            self.log(logging.INFO, f"Got {page_numbers} as number of pages in "
                     f"{round(time.monotonic() - start_time, 2)} seconds.")

            # get all the links for comics on the checklist
            self.logger_queue.put(("links", page_numbers))
            start_time = time.monotonic()
            comic_links = sum(self.poolmap(self.get_comic_links,
                                           list(range(1, page_numbers + 1))), [])
            comic_links = [link for link in comic_links
                           if isinstance(link, str)]
            self.log(logging.INFO, f"Got {len(comic_links)} comic links in "
                     f"{round(time.monotonic() - start_time, 2)} seconds.")

            # get the data for the comics
            self.logger_queue.put(("info", len(comic_links)))
            start_time = time.monotonic()
            comic_data = self.poolmap(self.get_comic_information, comic_links)
            self.log(logging.INFO, f"Got information about {len(comic_data)} "
                     f"comics in {round(time.monotonic() - start_time, 2)} seconds.")

            # get the images for the comic
            self.logger_queue.put(("image", len(comic_data)))
            start_time = time.monotonic()
            comic_images = self.poolmap(self.get_comic_image, [comic["Bildlink"]
                                                               for comic in comic_data])
            self.log(logging.INFO, f"Got {len(comic_images)} images in "
                     f"{round(time.monotonic() - start_time, 2)} seconds.")

            # store data in JSON file
            start_time = time.monotonic()
            for comic, image in zip(comic_data, comic_images):
                comic["Bild"] = image
            comics = {"_default": {str(index): comic
                                   for index, comic in enumerate(comic_data)}}
            with open("comics.json", "w", encoding="utf-8") as file:
                json.dump(comics, file)
            self.log(logging.INFO, f"Saved {len(comics['_default'])} comics to "
                     f"file in {round(time.monotonic() - start_time, 2)} seconds.")

            # stop logging
            self.logger_queue.put(False)
            log_proc.join()
        except (KeyboardInterrupt, Exception) as excp:  # pylint: disable=broad-except
            self.log(logging.ERROR, f"{excp.__class__.__name__}: {excp}")
            # also stop logging
            self.logger_queue.put(False)
            log_proc.join()
            self.log(logging.INFO, "Exiting.")


if __name__ == "__main__":
    Apollo().main()

# TODO:
# - better logging for errors
# - better error handling
# - catch individual errors
# - allow keyboard interrupt
# - make code a bit more readable
# - clean up comments and doc-strings
# - fix typing
