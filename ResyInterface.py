import pandas as pd, requests, io, re, csv, datetime, sys, json, html, math

import time, sched
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

def getResyPage(url, times) :
    print("function reached")
    print(url)
    print(times)
    content = rd.getPage(url, times)
    return content

def print_event(name):
    print('EVENT:', time.time(), name)

def main() :


    ## *** CONFIG ** ##

    ## INPUTS FOR RESERVATION DETAILS ##

    best = "7:00" ## Ideal time (will try to get as close to this time as possible)
    early = "6:00" ## Earliest possible time
    late = "9:30" ## latest possible time
    restaurant_url_code = "lartusi-ny" ## Name of Restaurant (type carefully)
    res_date = date.today() ## Date of Reservation (use date.today() for current date)
    num_people = 4 ## Number of people attending

    ## RUNTIME DETAILS ##
    # TODO: Once cloud infra is set need to add a date field here
    day = date.today()
    t_test = "2:14:00"
    t_lartusi = "08:59:58"

    ## live time variable ##
    t = t_test
    ## live time variable ##

    runtime = time.strptime("{0} {1}".format(day, t), "%Y-%m-%d %H:%M:%S")
    runtime_epoch = time.mktime(runtime)
    print(runtime)
    print(runtime_epoch)

    #s = sched.scheduler(time.time, time.sleep)

    arr = rd.getPreferredTimes(best, early, late)
    print(arr)

    datestring = "{0}-{1}-{2}".format(res_date.year, res_date.month, res_date.day)

    url1 = "https://resy.com/"
    url2 = "https://resy.com/cities/new-york-ny/venues/{1}?seats={2}&date={0}".format(datestring, restaurant_url_code, num_people)

    #content = s.enterabs(runtime_epoch, 1, getResyPage, argument=(url2, arr))
    #content = s.enterabs(runtime_epoch, 1, print_event, argument=("x"))

    #s.run()

    content = rd.getPage(url2, arr)

main()