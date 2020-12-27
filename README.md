Problem
-------
My small library at home is not diverse enough and I should read more.

And hey: It's lock down and COVID-19 and … and I really have time in the evening.

Solution
--------
Buy random books from medimops (a seller of used books popular in Germany).

It sends you an email with a PayPal link after the script has been run to pay your order.

The `library.json` file contains a library of your bought books, so you don't buy a book (title and author) more
than once.

Config
------

The `config.json` file should look like:

```
{
  "min_prize": 10,  
  "url": "https://www.medimops.de/buecher-belletristik-C0117/?condition=UsedGood%2CUsedVeryGood&listorder=asc&listorderby=oxvarminprice&searchparam=reclam&pgNr=$PAGE$",
  "max_page": 40,
  "max_prize": 3.50,
  "mail": "***",
  "password": "***",
  "sender": "***",
  "sender_smtp": "***",
  "sender_password": "***",
  "excluded_title_words": ["XL", "lernen", "Erläuterung", "Kontext", "Lehre", "Studien", "Anhang", "anhang"]
}
```

property    | description
------------|----------------------------------------------------------
`min_prize` | the minimal prize of your random order. It's 10€ by default, as this is the minimal amount for which medimops doesn't charge additional fees
`url`       | an url that consists of a search page of medimops in which `$PAGE$` is programatically replaced by a random page number, it is useful to sort ascending by prize, the given URL searches for Reclam books
`max_page`  | maximum page number, obtain it by hand
`max_prize` | maximum prize of a single book
`mail`      | mail to send the PayPal link to that is also the username for medimops
`password`  | password for medimops
`sender`    | sender of the mails
`sender_smtp` | SMTP server for sending the mails
`sender_password` | password for the SMTP server
`excluded_title_words` | a list of words that aren't aloud to be part of a title, my current list filters for words that might suggest books specifically made for students

The overall prize of an order is between `min_prize` and `min_prize` + `max_prize` (i.e. it doesn't do any bin packing)

Installation
------------
You only need BeautifulSoup and requests (and python3.8+), run `pip3 install -r requirements.txt` if needed.

Usage
-----

Create a config file first.

If you just want to test your config, run the `python3 dry_run.py`, an example output is:

```
➜  reclam python3 dry_run.py
Add Book(title='Immensee und andere Novellen', author='Theodor Storm') (2.97€) to basket
Add Book(title='Fontane zum Vergnügen: "Alles kommt auf die Beleuchtung an"', author='Christian Grawe') (3.01€) to basket
Add Book(title='Die junge Maria Stuart', author='Herbert Rosendorfer') (3.32€) to basket
Add Book(title='Berlin, mit deinen frechen Feuern: 100 Berlin-Gedichte', author='Michael Speier') (3.12€) to basket
```

Use `python3 reclam.py` to add some random books to your cart. Please don't look into your cart, as this would
reduce the fun…

Inspiration
-----------
This whole project is inspired by an XKCD comic:

![https://imgs.xkcd.com/comics/packages.png ](https://imgs.xkcd.com/comics/packages.png)

License
-------
Plain old MIT