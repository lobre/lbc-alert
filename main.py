#!/usr/local/bin/python

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from email.mime.text import MIMEText
from email.header import Header
import requests
import smtplib
import json
import sys
import hashlib
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = "template.html"
SETTINGS_FILE = "settings.json"
HASH_FILE = "hash.json"

# Change to script directory
os.chdir(SCRIPT_DIR)

# Settings
settings = {}
try:
    with open(SETTINGS_FILE, encoding='utf-8') as data_file:    
        settings = json.load(data_file)
except FileNotFoundError:
    print('Settings file not found')
    sys.exit(1)


def sendMail(to, subject, body):
    username = settings["gmail"]["username"]
    password = settings["gmail"]["password"]

    msg = MIMEText(body.encode('utf-8'), 'html', 'utf-8')
    msg['From'] = username
    msg['To'] = ','.join(to)
    msg['Subject'] = Header(subject, 'utf-8')

    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username, password)
    server.sendmail(username, to, msg.as_string())
    server.quit()


class Car:
    def __init__(self, title, link, location, price, date, image):
        self.title = title
        self.link = link
        self.location = location
        self.price = price
        self.date = date
        self.image = image
        self.mileage = None
        self.year = None
        self.description = None

    def __str__(self):
        return "{} | {} | {}".format(self.title, self.price, self.date)

    def hash(self):
        key = ''.join([self.title, self.location, self.price])
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def hasAnyKeyword(self):
        return any(keyword.lower() in self.description.lower() for keyword in settings["keywords"])

class CarParser:
    def __init__(self, url):
        self.url = url
        self.hash = []
        self.notify = []

        try:
            with open(HASH_FILE, encoding='utf-8') as hash_file:    
                self.hash = json.load(hash_file)
        except FileNotFoundError:
            print('No hash file found, creating it')


    def parse(self):
        try:
            r = requests.get(self.url)
        except requests.exceptions.RequestException as e:
            print("Connection error")
            sys.exit(1)

        data = r.text

        soup = BeautifulSoup(data, "html.parser")

        items = soup.select(".mainList .tabsContent a.list_item")

        for _, item in zip(range(settings["limit"]), items):

            title = item.section.h2.get_text().strip()
            link = "https:" + item.get("href")
            location = item.find('section', attrs={'class': 'item_infos'}).find_all('p')[1].get_text(strip=True)
            location = ' '.join(location.split())
            price = item.find('section', attrs={'class': 'item_infos'}).find('h3', attrs={'class': 'item_price'}).get_text(strip=True)
            date = item.find('section', attrs={'class': 'item_infos'}).find('aside', attrs={'class': 'item_absolute'}).find('p', attrs={'class': 'item_supp'}).get_text(strip=True)
            image = item.find('div', attrs={'class': 'item_image'}).find('span', attrs={'class': 'item_imagePic'}).find('span')
            image = "https:" + image.get('data-imgsrc') if image is not None else None

            car = Car(title, link, location, price, date, image)
            self.__fetchCarDetails(car)

            # Check if already seen
            if car.hash() not in self.hash:
                if not settings["use_keywords"] or car.hasAnyKeyword():
                    self.hash.append(car.hash())
                    self.notify.append(car)
            else:
                break

        if self.notify:
            self.__notify()

        with open(HASH_FILE, 'w+', encoding='utf-8') as outfile:
            json.dump(self.hash, outfile)

    def __fetchCarDetails(self, car):

        try:
            r = requests.get(car.link)
        except requests.exceptions.RequestException as e:
            print("Connection error")
            sys.exit(1)

        data = r.text
        soup = BeautifulSoup(data, "lxml")

        grid = soup.select("section.adview_main")[0]

        milage = grid.find_all("div", attrs={'class': 'line'})[6].find('h2').find('span', attrs={'class': 'value'}).get_text(strip=True)
        year = grid.find_all("div", attrs={'class': 'line'})[5].find('h2').find('span', attrs={'class': 'value'}).get_text(strip=True)
        description = str(grid.find_all("p", attrs={'itemprop': 'description'})[0])

        car.milage = milage
        car.year = year
        car.description = description

    def __notify(self):
        # send mail
        env = Environment(loader=FileSystemLoader(SCRIPT_DIR), trim_blocks=True)
        content = env.get_template(TEMPLATE_FILE).render(cars=self.notify)
        sendMail(settings["notifications"], settings["email_subject"], content)

        # print
        for car in self.notify:
            print("New car: {}".format(car.title))
    
car_parser = CarParser(settings["url"])
car_parser.parse()
