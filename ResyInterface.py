import wx

import pandas as pd, requests, io, re, csv, datetime, sys, json, html, math

import time
from datetime import date

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import ResyTimeFunctions as rtf
import ResyRestaurantLookup as rrl
import ResyDaemon as rd

def main() :


    ## *** CONFIG ** ##

    ## INPUTS FOR RESERVATION DETAILS ##

    best = "7:00" ## Ideal time (will try to get as close to this time as possible)
    early = "6:00" ## Earliest possible time
    late = "9:30" ## latest possible time
    restaurant_url_code = "loulou" ## Name of Restaurant (type carefully)
    res_date = date.today() ## Date of Reservation (use date.today() for current date)
    num_people = 2 ## Number of people attending

    arr = rd.getPreferredTimes(best, early, late)
    print(arr)

    datestring = "{0}-{1}-{2}".format(res_date.year, res_date.month, res_date.day)

    url1 = "https://resy.com/"
    url2 = "https://resy.com/cities/new-york-ny/venues/{1}?seats=2&date={0}".format(datestring, restaurant_url_code)
    content = rd.getPage(url2, arr)

main()