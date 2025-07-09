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


from src.domains.models import profile, user, reservationRequest




def csvToDataframe(file) :
	data = pd.read_csv(file, dtype='string')
	data_top = data.head()
	return data




def main() :
	platforms = csvToDataframe("data/verified_platforms.csv")
	print(platforms)
	


main()
