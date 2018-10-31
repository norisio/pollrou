import os

import datetime
import time

import requests
import json
import pickle

from selenium import webdriver
import traceback
from selenium.webdriver.support.ui import Select
import selenium.common.exceptions


webhook_url = os.environ['POLLROU_WEBHOOK_URL']
rsvrou_url = os.environ['POLLROU_RSVROU_URL']
chromedriver_path = os.environ['POLLROU_CHROMEDRIVER_PATH']

def post_message(text):
    requests.post(webhook_url, data=json.dumps({ 'text': text, 'username': 'ぽーる郎' }))

def get_tasks():
    ''' 翌月末までのタスクを取得 '''
    try:
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        driver = webdriver.Chrome(executable_path=chromedriver_path, chrome_options=chrome_option)
        driver.get(rsvrou_url)
        driver.execute_script("OnTab2Click()")
        Select(driver.find_element_by_id('drop_items')).select_by_value('a')

        year = time.localtime().tm_year
        month = time.localtime().tm_mon

        tasks = []

        def iterate_days():
            for i in range(35):
                cell = driver.find_element_by_id(f'cell{i}')
                try:
                    a = cell.find_element_by_tag_name('a')
                    sches = cell.find_element_by_class_name('sches')
                except selenium.common.exceptions.NoSuchElementException:
                    continue
                day = a.text
                try:
                    trs = sches.find_element_by_xpath('.//tbody').find_elements_by_tag_name('tr')
                except selenium.common.exceptions.NoSuchElementException:
                    continue
                for tr in trs:
                    time_str = tr.find_element_by_xpath('./td[1]').text
                    description_str = tr.find_element_by_xpath('./td[2]').text
                    begins = time.strptime(f"{year} {month} {day} {time_str}", "%Y %m %d %H:%M")
                    tasks.append( (begins, description_str) )

        iterate_days()
        driver.execute_script('OnCvNext(1)')
        month = month+1
        if month == 13:
            month = 1
            year = year + 1
        iterate_days()
    except:
        print (traceback.format_exc())
    return tasks

def compare_tasks_and_notify(old_tasks, new_tasks):
    for task in new_tasks:
        if not task in old_tasks:
            begins_str = time.strftime('%m/%d %H:%M', task[0])
            description_str = task[1]
            print(f'Found new task: {description_str}')
            post_message(f'New Appointment!\nBegins: {begins_str}\n{description_str}')

    for task in old_tasks:
        if not task in new_tasks:
            begins_str = time.strftime('%m/%d %H:%M', task[0])
            description_str = task[1]
            print(f'Found deleted task: {description_str}')
            post_message(f'Appointment Deleted.\n{begins_str} {description_str}')



def notify_todays_task(new_tasks):
    for task in new_tasks:
        task_time = task[0]
        task_date = datetime.date(task_time.tm_year, task_time.tm_mon, task_time.tm_mday)
        today_date = datetime.date.today()

        begins_str = time.strftime('%m/%d %H:%M', task[0])
        description_str = task[1]

        if task_date == today_date:
            post_message(f'Today\'s Appointment Notification.\nBegins: {begins_str}\n{description_str}')

def main():
    pickle_filename = 'old_tasks.bin'
    last_launched_filename = 'last_launched.txt'


    new_tasks = get_tasks()

    # 旧情報ピクルスがあれば読み込み
    if os.path.exists(pickle_filename):
        with open(pickle_filename, 'rb') as f:
            old_tasks = pickle.load(f)
    else:
        old_tasks = []

    compare_tasks_and_notify(old_tasks, new_tasks)

    # 旧情報ピクルスに保存
    with open(pickle_filename, 'wb') as f:
        pickle.dump(new_tasks, f, pickle.HIGHEST_PROTOCOL)


    # 1日の最初の起動時に当日のタスクを通知
    if os.path.exists(last_launched_filename):
        with open(last_launched_filename, 'r') as f:
            last_launched_str = f.readline().replace('\n', '')
    else:
        last_launched_str = '20181001'
    last_launched_date = datetime.datetime.strptime(last_launched_str, '%Y%m%d').date()

    if last_launched_date < datetime.date.today():
        notify_todays_task(new_tasks)

    with open(last_launched_filename, 'w') as f:
        f.write(time.strftime('%Y%m%d') + '\n')

if __name__ == '__main__':
    main()
