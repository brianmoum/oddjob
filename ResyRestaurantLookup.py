from bs4 import BeautifulSoup
import pandas as pd, requests, io, re, csv, datetime, sys, json, html

import time 
from datetime import date
 
import pandas as pd 
from selenium import webdriver 
from selenium.webdriver import Chrome 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json, sys, math

import ResyTimeFunctions as rtf

## Group of functions to take in a string of a restuarant name, lookup restaurant and navigate to restaurant reservation page, and then save the String name and the url code in a file.

def venuePageLookup(name) :

	with open('config.json') as f:
   		auth = json.load(f)

	## Options for webdriver ##

	options = webdriver.ChromeOptions()
	options.add_argument('--disable-blink-features=AutomationControlled')

	chrome_path = ChromeDriverManager().install()
	chrome_service = Service(chrome_path)

	driver = Chrome(options=options, service=chrome_service)

	driver.get("https://resy.com/cities/new-york-ny/search?query={0}".format(name))

	results = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "SearchResultsContainer")))

	## CASE: No Results
	try :
		if results.find_element(By.CLASS_NAME, "NoResults") :
			print("No Results Found.")
			return None

	except :
		pass

	## CASE: One Result

	items_container = results.find_element(By.CLASS_NAME, "SearchResultsContainer__results")

	items = items_container.find_elements(By.CSS_SELECTOR, "div.SearchResult__primary")

	print(len(items))

	venues = []
	for i in items :
		venue = i.find_element(By.CLASS_NAME, "SearchResult__container-link")
		name = venue.text
		print(name)
		url = venue.get_attribute("href")
		url = url.split("?")
		url = url[0]

		venues.append([name, url])


	return venues