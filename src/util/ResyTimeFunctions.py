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

