from flask import Flask, send_file, render_template, request
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from io import BytesIO
import os
import pandas as pd
import time
import logging

app = Flask(__name__)

# MongoDB connection
client = MongoClient('mongodb+srv://arsh123:Arsh123#@cluster0.xd59iuf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['your_database']
followers_collection = db['followers']

def initialize_webdriver():
    firefox_options = Options()
    firefox_options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'  # Path to Firefox binary
    firefox_options.accept_insecure_certs = True
    firefox_options.headless = False  # Set to True for headless mode, False to view browser
    gecko_driver_path = r'C:\windows\geckodriver.exe'  # Adjust the path if necessary

    driver = webdriver.Firefox(service=Service(gecko_driver_path), options=firefox_options)
    return driver

def login_to_twitter(driver, username, password, email=None):
    login_url = 'https://x.com/login'
    driver.get(login_url)

    try:
        username_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@name='text']"))
        )
        username_input.send_keys(username)
        username_input.send_keys(Keys.RETURN)

        try:
            email_input = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//input[@name='text' and @inputmode='text']"))
            )
            if email and email_input:
                email_input.send_keys(email)
                email_input.send_keys(Keys.RETURN)
        except:
            pass

        password_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@name='password']"))
        )
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        WebDriverWait(driver, 10).until(EC.url_changes(login_url))
        time.sleep(5)  # Wait for the login process to complete
    except Exception as e:
        print(f"Login error: {e}")
        driver.quit()


# Assuming you've already initialized 'client' and 'db' as MongoDB client and database
root_follower_data = {'username': '', 'followers': []}
def fetch_followers(driver, target_username, search_keyword, depth=2, initial=True):
    # Initialize data structure to store followers
    root_follower_data['username']=target_username

    if initial:
        # Directly navigate to the profile page
        try:
            profile_url = f"https://x.com/{target_username}"
            driver.get(profile_url)
            time.sleep(5)
        except Exception as e:
            print(f"Error navigating to profile page: {e}")
            return []

        # Navigate to the followers page
        try:
            followers_url = driver.current_url + '/followers'
            driver.get(followers_url)
            time.sleep(5)
        except Exception as e:
            print(f"Error navigating to followers page: {e}")
            return []

    followers = []
    last_height = driver.execute_script("return document.body.scrollHeight")

    # Scroll and collect follower links
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    follower_links = []
    try:
        followers_section = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//div/div/div[2]/main/div/div/div/div[1]/div/section/div/div/div[1]/div/div/button/div/div[2]/div/div[1]/div/div[1]/a/div/div[1]/span/span[1]"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for follower in soup.find_all('a', href=True, class_='css-175oi2r r-1wbh5a2 r-dnmrzs r-1ny4l3l r-1loqt21'):
            follower_links.append(follower['href'])
    except Exception as e:
        print(f"Error locating follower links: {e}")

    visited_links = set()
    for link in follower_links:
        if link in visited_links:
            continue
        visited_links.add(link)

        driver.get(f"https://x.com{link}")
        time.sleep(5)

        follower_data = {}
        try:
            # Scrape follower details
            try:
                name_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div/div/div/div[2]/div[1]/div/div[1]/div/div/span/span[1]"))
                )
                follower_data['name'] = name_element.text.strip()
            except Exception as e:
                print(f"Error scraping name: {e}")

            try:
                bio_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div/div/div/div[3]/div/div"))
                )
                follower_data['bio'] = bio_element.text.strip()
            except Exception as e:
                print(f"Error scraping bio: {e}")

            try:
                profession_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//button/span[contains(@class, 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3')]"))
                )
                follower_data['profession'] = profession_element.text.strip()
            except Exception as e:
                print(f"Error scraping profession: {e}")

            try:
                location_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//span[@data-testid='UserLocation']//span[contains(@class, 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3')]"))
                )
                follower_data['location'] = location_element.text.strip()
            except Exception as e:
                print(f"Error scraping location: {e}")

            try:
                join_date_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//span[@data-testid='UserJoinDate']/span[contains(@class, 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3')]"))
                )
                follower_data['join_date'] = join_date_element.text.strip()
            except Exception as e:
                print(f"Error scraping join date: {e}")

            try:
                contact_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//a[@data-testid='UserUrl']/span[contains(@class, 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3')]"))
                )
                follower_data['contact_link'] = contact_element.text.strip()
            except Exception as e:
                print(f"Error scraping contact link: {e}")
            
            try:
                followers_count_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div/div/div/div[5]/div[2]/a"))
                )
                follower_data['followers_count'] = followers_count_element.text.strip()
            except Exception as e:
                print(f"Error scraping followers count: {e}")

            try:
                following_count_element = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div/div/div/div[5]/div[1]/a"))
                )
                follower_data['following_count'] = following_count_element.text.strip()
            except Exception as e:
                print(f"Error scraping following count: {e}")

            concatenated_data = ' '.join(follower_data.values()).lower()

            # Check if username matches the search keyword
            if search_keyword.lower() in concatenated_data:
                
                # Store follower in MongoDB and fetch their followers recursively
                if depth > 1:
                    # Navigate directly to the current follower's followers page
                    followers_url = driver.current_url + '/followers'
                    driver.get(followers_url)
                    time.sleep(5)
                    
                    follower_data['followers'] = fetch_followers(driver, follower_data['name'], search_keyword, depth - 1, initial=False)
                followers_collection.insert_one(follower_data) 
                root_follower_data['followers'].append(follower_data)
                
            else:
                if depth > 1:
                # Store follower separately
                    followers_collection.insert_one(follower_data)

            # Add the follower data to the root follower's list
            root_follower_data['followers'].append(follower_data)
            
        except Exception as e:
            print(f"Error fetching follower data: {e}")
            continue

    return root_follower_data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_followers', methods=['POST'])
def fetch_followers_route():
    username = request.form['username']
    email = request.form.get('email')
    password = request.form['password']
    target_username = request.form['target_username']
    
    logging.debug(f"Fetching followers for: {target_username}")
    driver = initialize_webdriver()
    login_to_twitter(driver, username, password, email)
    root_follower_data = fetch_followers(driver, target_username, target_username)
    driver.quit()

    logging.debug(f"Fetched followers: {root_follower_data}")
    message = "Follower data fetched and stored successfully."    
    return render_template('followers.html', message=message)

if __name__ == "__main__":
    app.run(debug=True)
