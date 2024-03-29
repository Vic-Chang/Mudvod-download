import argparse
import os
import shutil
import requests
import time
import m3u8
import queue
import threading
import re
import colorama
import signal
import sys
from colorama import Fore
from functools import cmp_to_key
from playwright.sync_api import sync_playwright

# Auto reset color after output every line
colorama.init(autoreset=True)
que = queue.Queue()
request = requests.session()

TEMP_TS_FOLDER = 'temp_ts'
TEMP_TS_LIST_TXT = 'temp_ts_list.txt'


def remove_temp_data() -> None:
    """
    Remove temp files if exist
    """
    if os.path.exists(TEMP_TS_FOLDER):
        shutil.rmtree(TEMP_TS_FOLDER, ignore_errors=True)
    if os.path.exists(TEMP_TS_LIST_TXT):
        os.remove(TEMP_TS_LIST_TXT)


def signal_handler(stop_signal, frame) -> None:
    """
    Remove all temp files before user cancel the program
    """
    print(f'\n{Fore.RED}You have stopped the program.')
    # Delay a seconds, waiting for all temp files write to disk
    time.sleep(2)
    remove_temp_data()
    sys.exit(0)


remove_temp_data()
os.mkdir(TEMP_TS_FOLDER)

signal.signal(signal.SIGINT, signal_handler)


def get_all_ts_files_url(m3u8_url: str) -> None:
    """
    Get all of ts files url from m3u8 url, and save ts files url results to the que.
    :param m3u8_url: m3u8 urk
    :return:  Save ts files url to the que
    """
    playlist = m3u8.load(m3u8_url)
    for item in playlist.segments:
        que.put(item.uri)
    print('Set all ts files url in que !')


def download_ts_file() -> None:
    """
    Download ts files from que
    """
    while not que.empty():
        ts_url = que.get()
        file_name = os.path.basename(ts_url).split("?")[0]
        with request.get(ts_url, stream=True) as r:
            r.raise_for_status()
            with open(os.path.join(TEMP_TS_FOLDER, file_name), 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)


def download_ts_file_job() -> None:
    """
    The thread download job, create multiple thread to download ts files
    """
    total_files_count = que.qsize()
    completed_file_count = 0
    threads = []
    thread_count = 10
    if total_files_count < thread_count:
        thread_count = total_files_count

    for _ in range(thread_count):
        t = threading.Thread(target=download_ts_file)
        t.daemon = True
        threads.append(t)
    for t in threads:
        t.start()
    print('All threading are starts !')
    print(f'\r{Fore.YELLOW}Download progress  ... {(completed_file_count / total_files_count) * 100} %', end="")
    for t in threads:
        t.join()
        completed_file_count = completed_file_count + 1
        print(f'\r{Fore.YELLOW}Download progress... {round((completed_file_count / total_files_count) * 100, 2)} %',
              end="")
    print(f'')
    print('All threading are done !')
    print(f'{Fore.GREEN}Ts files download Complete !')


def all_ts_to_txt_file(func):
    """
    Get all ts files name and list it into txt file in order
    :return: Out a txt file with all ts files name in order
    """
    pattern = re.compile(r'(?<=\D)\d+(?=[.ts])')

    def name_compare(file1, file2):
        """
        TS files name custom sort, sort by file number
        :param file1: TS file 1
        :param file2: TS file 2
        :return: File name compare by file name number
        """
        result1 = pattern.search(str(file1))
        result2 = pattern.search(str(file2))
        if result1 is None:
            return -1
        else:
            number1 = int(result1[0])

        if result2 is None:
            return -1
        else:
            number2 = int(result2[0])

        if number1 < number2:
            return -1
        else:
            return 1

    def is_ts_file(file_name) -> bool:
        """
        Check ts file name is valid, file name rule is `XXXX_0000.ts`
        :param file_name: file name
        :return: is file valid
        """
        if file_name.split('.')[-1].lower() != 'ts':
            return False

        if not os.path.isfile(os.path.join(TEMP_TS_FOLDER, file_name)):
            return False

        if pattern.search(str(file_name)) is None:
            return False

        return True

    def wrap(*args, **kwargs):
        # Get all files name and remove useless and order files by file name
        files_name_list = [file_name for file_name in os.listdir(TEMP_TS_FOLDER) if is_ts_file(file_name)]
        files_name_list.sort(key=cmp_to_key(name_compare))

        with open(TEMP_TS_LIST_TXT, 'w') as f:
            f.writelines((f"file '{os.path.join(TEMP_TS_FOLDER, file_name)}'\r" for file_name in files_name_list))

        func(*args, **kwargs)

        # Start to delete all temp files
        remove_temp_data()

    return wrap


@all_ts_to_txt_file
def merge_all_ts_files(output_video_name) -> None:
    """
    Merge all ts files to one mp4 file
    :return: Out a mp4 video file
    """

    print('_____________________________')
    print('Start combine all ts files...')
    # Use -y to force overwrite file if fild exists
    # Use loglevel quite to hide output
    os.system(
        f'ffmpeg -y -f concat -safe 0 -loglevel quiet -i {TEMP_TS_LIST_TXT} -c copy -bsf:a aac_adtstoasc "{output_video_name}.mp4"')
    print(f'{Fore.GREEN}Combine ts files complete !')
    print('_____________________________')
    print(f'{Fore.GREEN}The video file has been saved to the program folder !')


def open_browser_to_get_m3u8(url) -> tuple:
    """
    It will open a browser to get the video's m3u8 url from network requests
    :param url: Video url
    :return: A tuple, Video name , M3u8 url
    """
    m3u8_url = ''
    skip_ad = True

    def on_network_request(network_request) -> None:
        """
        Get the m3u8 url from browser's network requests.
        The first m3u8 url is ad, so get the second url
        """
        nonlocal m3u8_url
        nonlocal skip_ad
        if 'm3u8' in network_request.url:
            if skip_ad:
                skip_ad = False
                return
            m3u8_url = network_request.url

    with sync_playwright() as p:
        print('Process start !')
        # Use firefox browser, chromium can't be play video (show flash video not support)
        browser = p.firefox.launch(headless=False, devtools=False)
        page = browser.new_page()

        print(f'{Fore.GREEN}Start capturing specific video url...')
        page.on('request', on_network_request)
        page.goto(url)
        # Wait for render movie title
        title_element = page.wait_for_selector('.title-link')
        video_title = title_element.inner_text()
        # Wait for close ad video
        page.wait_for_selector('.v-ad-detail', state='detached')
        # Wait a seconds
        page.wait_for_timeout(1 * 1000)
        page.close()
        browser.close()
    return video_title, m3u8_url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', type=str, help='Video url')
    args = parser.parse_args()

    video_url = args.url
    video_name, video_m3u8_url = open_browser_to_get_m3u8(video_url)
    get_all_ts_files_url(video_m3u8_url)
    download_ts_file_job()
    merge_all_ts_files(video_name)
