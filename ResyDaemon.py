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


## Look into Scrapy for polite Spider to potentially circumvent bot detection: https://docs.scrapy.org/en/latest/intro/overview.html


def timeToFloat(time_str) :

	## Checking to see if input is already a float and in the correct format. If it is a float but wrong format, simply rounds (this shouldn't ever happen but just covering edge case) ##
	if type(time_str) == float :
		if (int(time_str) == time_str) or not (time_str % .25) or not (time_str % .5) or not (time_str % .75) :
			return time_str
		else :
			return round(time_str)

	if " " in time_str :
		i = time_str.index(" ")
		time_str = time_str[:i]

	if "P" in time_str :
		i = time_str.index("P")
		time_str = time_str[:i]

	if "p" in time_str :
		i = time_str.index("p")
		time_str = time_str[:i]

	elif len(time_str) == 1 :
		time_str= time_str + ":00"

	if len(time_str) < 1 or len(time_str) > 8:
		print(time_str)
		print(len(time_str))
		print("Incorrect Time Format. Cannot Parse.")
		sys.exit()


	time_arr = time_str.split(":")

	time_float = float(time_arr[0])

	if time_arr[1] not in ["00", "15", "30", "45"] :
		mins = int(time_arr[1])
		mins_00 = abs(mins - 0)
		mins_15 = abs(mins - 15)
		mins_30 = abs(mins - 30)
		mins_45 = abs(mins - 45)
		mins_60 = abs(mins - 60)

		min_mins = min(mins_00, mins_15, mins_30, mins_45, mins_60)

		if min_mins == mins_00 :
			time_arr[1] = "00"
		elif min_mins == mins_15 :
			time_arr[1] = "15"
		elif min_mins == mins_30 :
			time_arr[1] = "30"
		elif min_mins == mins_45 :
			time_arr[1] = "45"
		elif min_mins == mins_60 :
			time_arr[1] = "00"

	if time_arr[1] == "00" :
		time_float += 0
	elif time_arr[1] == "15" :
		time_float += .25
	elif time_arr[1] == "30" :
		time_float += .5
	elif time_arr[1] == "45" :
		time_float += .75


	return time_float

def floatToTime(time_float) :

	hour = math.floor(time_float)

	if time_float == hour :
		mins = ":00 PM"
	elif time_float - .25 == hour :
		mins = ":15 PM"
	elif time_float - .5 == hour :
		mins = ":30 PM"
	elif time_float - .75 == hour :
		mins = ":45 PM"
	else :
		mins = ":00 PM"

	hour = str(hour)
	time_str = hour + mins

	return time_str

def toMilitaryTime(time_str) :
	time_float =  timeToFloat(time_str)
	time_float = time_float + 12
	mil_time_str = floatToTime(time_float)
	mil_time_str = mil_time_str[:5]
	mil_time_str += ":00"

	return mil_time_str

def getPreferredTimes(best, earliest, latest) :

	preferred_times = []

	n_best = timeToFloat(best)
	n_earliest = timeToFloat(earliest)
	n_latest = timeToFloat(latest)

	preferred_times.append(floatToTime(n_best))

	i = .25
	while True :
		upper_i = n_best + i
		lower_i = n_best - i

		if upper_i <= n_latest :
			preferred_times.append(floatToTime(upper_i))
		if lower_i >= n_earliest :
			preferred_times.append(floatToTime(lower_i))

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
				mt = toMilitaryTime(t)
				print(mt)
				button = driver.find_element(By.CSS_SELECTOR, ".ReservationButton[id*='{0}']".format(mt))
				print(button.text)
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
	print(cont.text)
	auth_container = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "AuthContainer")))
	print(auth_container.text)
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
	best = "7:00"
	early = "6:00"
	late = "9:30"
	arr = getPreferredTimes(best, early, late)
	print(arr)

	today = date.today()
	datestring = "{0}-{1}-{2}".format(today.year, today.month, today.day)

	url1 = "https://resy.com/"
	url2 = "https://resy.com/cities/new-york-ny/venues/loulou?seats=2&date={0}".format(datestring)
	content = getPage(url2, arr)

	print(content)
	for c in content :
		if "6:00 PM" in c.text :

			print(c.text)



main()