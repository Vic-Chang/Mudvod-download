import os
import requests
import m3u8
import queue
import threading
import re
from functools import cmp_to_key

que = queue.Queue()
request = requests.session()

temp_ts_folder = 'temp_ts'
if not os.path.exists(temp_ts_folder):
    os.mkdir(temp_ts_folder)
temp_ts_list_txt = 'temp_ts_list.txt'


def get_all_ts_files_url(m3u8_url: str):
    playlist = m3u8.load(m3u8_url)
    for item in playlist.segments:
        que.put(item.uri)
    print('Set all ts files url in que!')


def download_ts_file():
    while not que.empty():
        ts_url = que.get()
        file_name = os.path.basename(ts_url).split("?")[0]
        with request.get(ts_url, stream=True) as r:
            r.raise_for_status()
            with open(os.path.join(temp_ts_folder, file_name), 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)
                print(f'\r{threading.get_ident()}: Download success! {file_name}', end='')


def download_ts_file_job():
    threads = []
    for _ in range(10):
        t = threading.Thread(target=download_ts_file)
        t.daemon = True
        threads.append(t)
    for t in threads:
        t.start()
    print('All threading are starts!')
    for t in threads:
        t.join()
    print('All threading are done!')


def all_ts_to_txt_file():
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
        if file_name.split(".")[-1].lower() != 'ts':
            return False

        if not os.path.isfile(os.path.join(temp_ts_folder, file_name)):
            return False

        if pattern.search(str(file_name)) is None:
            return False

        return True

    files_name_list = [file_name for file_name in os.listdir(temp_ts_folder) if is_ts_file(file_name)]
    files_name_list.sort(key=cmp_to_key(name_compare))

    with open(temp_ts_list_txt, 'w') as f:
        f.writelines((f"file {os.path.join(temp_ts_folder, file_name)}\r" for file_name in files_name_list))


def merge_all_ts_files():
    """
    Merge all ts files to one mp4 file
    :return: Out a mp4 video file
    """
    print('Start combine all ts files...')
    os.system(f'ffmpeg -f concat -safe 0 -i {temp_ts_list_txt} -c copy -bsf:a aac_adtstoasc video.mp4')
    print('Combine complete!')


if __name__ == '__main__':
    url = 'https://api.mudvod.tv/play/mud.m3u8/WEB/1.0?ce=3d76b3c8ebe35fab3c99befd306549784905f386193c0b52828b78cc813f5e86f0aa88322792d75df7e355491ebed73547b335c7d82c9aec349fdfb9cf3083eb3840942db5c9f996f66caa590a34d14c4cc210ce21cab9d4e0af446b5a0e1b57eb3802d1399ac198640a9cb907d7f5982a2ab23fa0b4691a&pf=3&uk=249342639623064975fffa9b920fc0f9&rx=12460&expire=1658324453654&ip=118.163.56.205&sign=69fe0c580a9bfd281d6b622b77b7af74&_ts=1658299253654'
    get_all_ts_files_url(url)
    download_ts_file_job()
    all_ts_to_txt_file()
    merge_all_ts_files()
