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


## Look into Scrapy for polite Spider to potentially circumvent bot detection: https://docs.scrapy.org/en/latest/intro/overview.html

def getPreferredTimes(best, earliest, latest) :

	preferred_times = []

	n_best = rtf.timeToFloat(best)
	n_earliest = rtf.timeToFloat(earliest)
	n_latest = rtf.timeToFloat(latest)

	preferred_times.append(rtf.floatToTime(n_best))

	i = .25
	while True :
		upper_i = n_best + i
		lower_i = n_best - i

		if upper_i <= n_latest :
			preferred_times.append(rtf.floatToTime(upper_i))
		if lower_i >= n_earliest :
			preferred_times.append(rtf.floatToTime(lower_i))

		if upper_i >= n_latest and lower_i <= n_earliest :
			break

		i += 0.25

	return preferred_times


def getPage(url, preferred_times, attempt=0) :

	## Get Resy credentials from config file ##

	with open('config.json') as f:
   		auth = json.load(f)

	## Options for webdriver ##

	options = webdriver.ChromeOptions()
	options.add_argument('--disable-blink-features=AutomationControlled')

	chrome_path = ChromeDriverManager().install()
	chrome_service = Service(chrome_path)

	driver = Chrome(options=options, service=chrome_service)

	driver.get(url)
	selector = ""

	## Find best Reservation and click time button ##
	container = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "ShiftInventory__shift--last")))
	buttons = container.find_elements(By.CSS_SELECTOR, ".ReservationButton")

	button_keys = []
	for b in buttons :
		button_keys.append(b.text)

	done = False
	i = 0
	while not done :
		t = preferred_times[i]
		for b in button_keys :
			if t in b :
				mt = rtf.toMilitaryTime(t)
				button = driver.find_element(By.CSS_SELECTOR, ".ReservationButton[id*='{0}']".format(mt))
				button.click()

				done = True
				break
		i += 1

	iframe = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "iframe[title='Resy - Book Now']")))
	driver.switch_to.frame(iframe)
	reserve_now = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "Button.Button--primary.Button--lg")))
	reserve_now.click()

	try:
		reserve_now = driver.find_element(By.CSS_SELECTOR, "Button.Button--primary.Button--lg")

	except:
			reserve_now = None

	while reserve_now :
		try :
			reserve_now.click()
			time.sleep(.5)
		except :
			break

	## Logging into Resy account with username and password ##

	#login = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "Button--login")))
	#login.click()
	cont = driver.find_element(By.CLASS_NAME, "AuthContainer")
	auth_container = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "AuthContainer")))
	un_pw_container = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "AuthView__Footer")))
	un_pw_button = un_pw_container.find_element(By.CSS_SELECTOR, "button")
	un_pw_button.click()

	login_form = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "LoginForm")))

	email = login_form.find_element(By.ID, "email")
	email.clear()
	email.send_keys(auth["username"])

	pwd = login_form.find_element(By.NAME, "password")
	pwd.clear()
	pwd.send_keys(auth["password"])

	login_button = login_form.find_element(By.CLASS_NAME, "Button--lg")
	login_button.click()

	time.sleep(5)

def main() :

	## INPUTS FOR RESERVATION DETAILS ##

	best = "7:00" ## Ideal time (will try to get as close to this time as possible)
	early = "6:00" ## Earliest possible time
	late = "9:30" ## latest possible time
	restaurant_url_code = "loulou" ## Name of Restaurant (type carefully)
	res_date = date.today() ## Date of Reservation
	num_people = 2 ## Number of people attending

	arr = getPreferredTimes(best, early, late)
	print(arr)

	datestring = "{0}-{1}-{2}".format(res_date.year, res_date.month, res_date.day)

	url1 = "https://resy.com/"
	url2 = "https://resy.com/cities/new-york-ny/venues/{1}?seats=2&date={0}".format(datestring, restaurant_url_code)
	content = getPage(url2, arr)



main()