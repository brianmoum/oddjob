from bs4 import BeautifulSoup
import pandas as pd, requests, io, re, csv, datetime, sys, json, html

import time 
 
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



def getPage(url, attempt=0) :

	print(url)

	options = webdriver.ChromeOptions()
	options.add_argument('--disable-blink-features=AutomationControlled')
	#options.add_argument('--headless')

	#options.page_load_strategy = 'none'

	chrome_path = ChromeDriverManager().install()
	chrome_service = Service(chrome_path)

	driver = Chrome(options=options, service=chrome_service)

	## Need to add explicit wait to driver; currently failing attempts to grab reservation buttos because the elements have not loaded yet


	driver.get(url)
	selector = ""
	## Content should use driver to pull desired elements. Need to inspect pages to determine what to pull. MLB REF was standard but for this might need to make dynamic somehow
	element = None
	try :
		element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "ShiftInventory__shift")))
	finally :
		driver.quit()
	#wrapper = driver.find_element(by=By.CLASS_NAME, value="ShiftInventory__shift--last")

	return element

def main() :
	url1 = "https://resy.com/"
	url2 = "https://resy.com/cities/new-york-ny/venues/le-gratin?seats=2&date=2024-04-30"
	content = getPage(url2)
	print(content.text)


main()