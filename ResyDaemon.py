from bs4 import BeautifulSoup
import pandas as pd, requests, io, re, csv, datetime, sys, json, mysql.connector, html

import time 
 
import pandas as pd 
from selenium import webdriver 
from selenium.webdriver import Chrome 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By 
from webdriver_manager.chrome import ChromeDriverManager

def getPage(url) :

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    options.page_load_strategy = 'none'

    chrome_path = ChromeDriverManager().install()
    chrome_service = Service(chrome_path)

    driver = Chrome(options=options, service=chrome_service)
    driver.implicitly_wait(10)
    driver.set_script_timeout(300)

    driver.get(url)
    ## Content should use driver to pull desired elements. Need to inspect pages to determine what to pull. MLB REF was standard but for this might need to make dynamic somehow

    #content = driver.find_elements(By.CSS_SELECTOR, "div[class*='table_container is_setup'")

    if not content :
        print("Content Failed to load; waiting to try again.")
        time.sleep(30)
        content = getPage(url)

    return content

def main() :
	pass