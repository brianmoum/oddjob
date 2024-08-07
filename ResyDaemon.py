from bs4 import BeautifulSoup
import pandas as pd, requests, io, re, csv, datetime, sys, json, html

import time 
from datetime import date

from selenium import webdriver 
from selenium.webdriver import Chrome 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json, sys, math

import ResyTimeFunctions as rtf


## TODO: Look into Scrapy for polite Spider to potentially circumvent bot detection: https://docs.scrapy.org/en/latest/intro/overview.html

def getPreferredTimes(best, earliest, latest) :
	## Creating array of every time within defined range, and ordering array from most preferred to least preferred (starting from "best time" and moving outward both earlier and later in increments of 15 mins until upper and lower boundaries are reached). ##
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

	## NOTE: below driver config worked initially but started to throw errors. Swapped for standard Chrome driver and that seemed to work
	#driver = Chrome(options=options, service=chrome_service)
	driver = Chrome()
	print("checkpoint")
	driver.get(url)
	selector = ""



	## Find best Reservation and click time button ##

	## NOTE: There are multiple "ShiftInventory" elements on the page for each service window (Brunch, Lunch, Dinner, etc.). Currently the "container" variable should always grab the element with "Dinner"
	## since the element being grabbed is explicitly the last "ShiftInventory" on the page ("ShiftInventory__shift--last"). Need to make this dynamic if we want to add functionality to enable user to
	## reserve other service windows.

	container = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "ShiftInventory__shift--last")))

	buttons = container.find_elements(By.CSS_SELECTOR, ".ReservationButton")

	if len(buttons) <= 0 :
		print("no times available on page.")
		sys.exit()
	else :
		print("times found")
		sys.exit()

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

	## Found issue where UI asks clarifying questions (e.g. 'confirm you want to sit outside'), so need to click button repeatedly until menu advances ##
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

