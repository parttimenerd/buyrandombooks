import datetime
import json
import random
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Callable, Optional

import requests
from bs4 import BeautifulSoup


def current_path() -> Path:
    return Path(__file__).parent


@dataclass(frozen=True)
class Book:
    title: str
    author: str


@dataclass(frozen=True)
class BuyInfo:
    date: str
    time: float
    prize: float


@dataclass
class Library:
    path: Path
    books: Dict[Book, BuyInfo]

    @staticmethod
    def load(path: Path = current_path() / "library.json") -> "Library":
        if not path.exists():
            return Library(path, {})
        with path.open() as f:
            return Library(path, {Book(d["title"], d["author"]): BuyInfo(d["date"], d["time"], d["prize"])
                                  for d in json.load(f)})

    def to_dict(self) -> dict:
        return [{"title": book.title, "author": book.author, "date": info.date, "time": info.time, "prize": info.prize}
                for book, info in self.books.items()]

    def store(self):
        with self.path.open("w") as f:
            json.dump(self.to_dict(), f, indent=4)

    def _add_book(self, book: Book, buy_info: BuyInfo):
        assert book not in self.books
        self.books[book] = buy_info
        self.store()

    def add_book(self, book: Book, prize: float):
        self._add_book(book, BuyInfo(datetime.datetime.today().strftime('%Y-%m-%d-%H:%M:%S'), time.time(), prize))

    def __contains__(self, book: Book) -> bool:
        return book in self.books


@dataclass(frozen=True)
class BookInfo:
    inputs: Dict[str, str]  # input field values
    prize: str


@dataclass
class Order:
    library: Library
    books: Dict[Book, BookInfo]

    def overall_prize(self) -> float:
        return sum(info.prize for info in self.books.values())


@dataclass
class Page:
    library: Library
    books: Dict[Book, BookInfo]

    @staticmethod
    def load_page(reclam: "Reclam", url: str) -> Optional["Page"]:
        page = Page(reclam.library, {})
        time.sleep(random.random() * 3)
        res = reclam.session.get(url, headers=reclam.headers(), timeout=3)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        for item in soup.select(".mx-product-list-item"):
            try:
                title = item.select(".mx-product-list-item-title")[0].text.strip()
                author = item.select(".mx-product-list-item-manufacturer-link")[0].text.strip()
                if any(item.select(f".sprite-icon-{i}") for i in ["audiobook", "music", "game", "movie"]):
                    # skip all non books
                    print(f"Skip non book {title} by {author}")
                    continue
                prize = float(
                    item.select(".mx-product-list-item-price")[0].text.strip().split(" ")[0].replace(",", "."))
                inputs = {i["name"]: i["value"] for i in item.select("form input")}
                page.books[Book(title, author)] = BookInfo(inputs, prize)
            except:
                pass
        return page

    def random_books(self, max_prize: float, book_filter: Callable[[Book, float], bool]) -> Dict[Book, BookInfo]:
        ret = {}
        av_books = list(b for b in self.books.keys() if b not in self.library)
        sum = 0
        while sum < max_prize and len(av_books) > 0:
            random.shuffle(av_books)
            chosen: Book = av_books[0]
            av_books.remove(chosen)
            info = self.books[chosen]
            if book_filter(chosen, info.prize):
                sum += info.prize
                ret[chosen] = info
        return ret


class Reclam:

    def __init__(self, library: Library = None, dry_run: bool = False):
        self.library = library or Library.load()
        self.session = requests.Session()
        self.order = Order(self.library, {})
        self.dry_run = dry_run

    def sleep(self):
        time.sleep(random.random() * 3)

    def headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0",
            "Upgrade-Insecure-Requests": "1",
            "TE": "Trailers",
            "Origin": "https://www.medimops.de",
            "Host": "www.medimops.de"
        }

    def login(self, mail: str, password: str):
        # Create the payload
        self.sleep()
        ret = self.session.post("https://www.medimops.de/Mein-Konto/", {
            "lgn_usr": mail,
            "lgn_pwd": password,
            "lang": "0",
            "listtype": "",
            "actcontrol": "account",
            "fnc": "login_noredirect",
            "cl": "account",
            "tpl": "",
            "mxSourceUrl": "https%3A%2F%2Fwww.medimops.de%2FMein-Konto%2F%3Fpromo%3D1"},
                                headers=self.headers())
        assert "falsches Passwort" not in BeautifulSoup(ret.text, "html.parser").text

    def add_to_basket(self, book: Book, info: BookInfo):
        self.sleep()
        if self.dry_run:
            print(f"Add {book} ({info.prize:.2f}€) to basket")
        self.order.books[book] = info
        if self.dry_run:
            return
        self.library.add_book(book, info.prize)
        self.session.post("https://www.medimops.de/", info.inputs, headers=self.headers())

    def add_random_books_to_basket(self, random_url: Callable, min_prize: float,
                                   book_filter: Callable[[Book, float], bool]):
        while self.order.overall_prize() < min_prize:
            page = Page.load_page(self, random_url())
            if not page:
                continue
            books = page.random_books(min_prize, book_filter)
            for book, info in books.items():
                if book not in self.order.books:
                    self.add_to_basket(book, info)

    def get_paypal_url(self) -> str:
        res = self.session.get("https://www.medimops.de/Warenkorb/", headers=self.headers())
        assert res.status_code == 200
        soup = BeautifulSoup(res.text, "html.parser")
        form = soup.select("form[data-ga-label=\"Paypal Express\"]")[0]
        res2 = self.session.post(form["action"],
                                 {i["name"]: i.get("value", "") for i in form.select("input") if i.get("value", "")},
                                 headers=self.headers())
        return res2.url

    def send_order_mail(self, recipient: str, sender: str, sender_smtp: str, sender_password: str):
        """ Send a mail with a link to the buy page """
        body = f"""Ordering {self.order.overall_prize():.2f} euros worth of books. 
Please pay at {self.get_paypal_url()}"""
        import smtplib
        """this is some test documentation in the function"""
        msg = EmailMessage()
        msg['Subject'] = "Buy some random books"
        msg['From'] = sender
        msg['To'] = recipient
        print(body)
        msg.set_content(body)
        # Send the mail
        server = smtplib.SMTP(host=sender_smtp, port=587)
        server.login(sender, sender_password)
        server.sendmail(sender, recipient, str(msg))
        server.quit()


def run(dry_run: bool = False):
    config_file = current_path() / "config.json"
    if not config_file.exists():
        raise BaseException(f"Config file {config_file} does not exist, see README for its format")
    config = json.load(config_file.open())
    reclam = Reclam(dry_run=dry_run)
    reclam.login(config["mail"], config["password"])
    reclam.add_random_books_to_basket(
        lambda: config["url"].replace("$PAGE$", str(random.randint(0, config["max_page"]))),
        min_prize=config["min_prize"],
        book_filter=lambda book, prize: not any(
            word in book.title for word in config["excluded_title_words"]) and prize < config["max_prize"])
    if not dry_run:
        reclam.send_order_mail(config["mail"], config["sender"], config["sender_smtp"], config["sender_password"])


if __name__ == '__main__':
    run(dry_run=False)
