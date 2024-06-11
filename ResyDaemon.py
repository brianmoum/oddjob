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


# ***** NOTE: Experienced multiple failed attempts to grab the desired element with selenium, being unable to grab the desired element even after waiting a full minute for page load. Made eventual progress after playing with browser options,
# specifically removing the headless option which actually loaded the page in a window, and received a new error which seems to suggest that the behavior of the script in its current form can be identified by the page as a bot, and is being
# kicked out. Need to look into and implement evasion methods as described here: https://stackoverflow.com/questions/71885891/urllib3-exceptions-maxretryerror-httpconnectionpoolhost-localhost-port-5958. *****

## Look into Scrapy for polite Spider to potentially circumvent bot detection: https://docs.scrapy.org/en/latest/intro/overview.html

def getPage(url, attempt=0) :

	print(url)

	options = webdriver.ChromeOptions()
	options.add_argument('--disable-blink-features=AutomationControlled')
	#options.add_argument('--headless')

	#options.page_load_strategy = 'none'

	chrome_path = ChromeDriverManager().install()
	chrome_service = Service(chrome_path)

	driver = Chrome(options=options, service=chrome_service)

	driver.get(url)
	selector = ""

	container = None
	container = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "ShiftInventory__shift")))

	buttons = container.find_elements(By.CSS_SELECTOR, ".ReservationButton")

	## TODO: function to take input of time preference and available times, and return sorted list of preferred times

	for b in buttons :
		if "6:00 PM" in b.text :
			b.click()
			time.sleep(5)


	return buttons

def main() :
	today = date.today()
	datestring = "{0}-{1}-{2}".format(today.year, today.month, today.day)

	url1 = "https://resy.com/"
	url2 = "https://resy.com/cities/new-york-ny/venues/le-gratin?seats=2&date={0}".format(datestring)
	content = getPage(url2)

	print(content)
	for c in content :
		if "6:00 PM" in c.text :

			print(c.text)



main()