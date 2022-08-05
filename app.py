import os
import shutil
import requests
import m3u8
import queue
import threading
import re
from functools import cmp_to_key

que = queue.Queue()
request = requests.session()

TEMP_TS_FOLDER = 'temp_ts'
TEMP_TS_LIST_TXT = 'temp_ts_list.txt'

# Remove old temp data if exist
if os.path.exists(TEMP_TS_FOLDER):
    shutil.rmtree(TEMP_TS_FOLDER, ignore_errors=True)
os.mkdir(TEMP_TS_FOLDER)


def get_all_ts_files_url(m3u8_url: str) -> None:
    """
    Get all of ts files url from m3u8 url, and save ts files url results to the que.
    :param m3u8_url: m3u8 urk
    :return:  Save ts files url to the que
    """
    playlist = m3u8.load(m3u8_url)
    for item in playlist.segments:
        que.put(item.uri)
    print('Set all ts files url in que!')


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
                print(f'{threading.get_ident()}: Download success! {file_name}')


def download_ts_file_job() -> None:
    """
    The thread download job, create multiple thread to download ts files
    """
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
        if file_name.split(".")[-1].lower() != 'ts':
            return False

        if not os.path.isfile(os.path.join(TEMP_TS_FOLDER, file_name)):
            return False

        if pattern.search(str(file_name)) is None:
            return False

        return True

    def wrap():
        # Get all files name and remove useless and order files by file name
        files_name_list = [file_name for file_name in os.listdir(TEMP_TS_FOLDER) if is_ts_file(file_name)]
        files_name_list.sort(key=cmp_to_key(name_compare))

        with open(TEMP_TS_LIST_TXT, 'w') as f:
            f.writelines((f"file '{os.path.join(TEMP_TS_FOLDER, file_name)}'\r" for file_name in files_name_list))

        func()

        # Start to delete all temp files
        os.remove(TEMP_TS_LIST_TXT)
        shutil.rmtree(TEMP_TS_FOLDER, ignore_errors=True)

    return wrap


@all_ts_to_txt_file
def merge_all_ts_files() -> None:
    """
    Merge all ts files to one mp4 file
    :return: Out a mp4 video file
    """

    print('Start combine all ts files...')
    os.system(f'ffmpeg -f concat -safe 0 -i {TEMP_TS_LIST_TXT} -c copy -bsf:a aac_adtstoasc video.mp4')
    print('Combine complete!')


if __name__ == '__main__':
    url = 'https://api.mudvod.tv/play/mud.m3u8/WEB/1.0?ce=922e59d341843d64edfcb4f68c4047fa32e8bd3f624a99179e61d2145ea29b85077490717c75a420867fb254c3380ad27bef336c1214cdb189929d38ab24483000b3de6222f2559ff5991bfa9039c702eb99c47a618d8f60fa35ef363882138e49a0564ac01ccf9550ad607f541d5d0ee671c6d0470d8cca&pf=3&uk=192e557fe6572e818ecac3b423eccbde&rx=7234&expire=1659696807889&ip=118.163.56.205&sign=458744e8555a883eaba8ec3e0f2e97e1&_ts=1659671607889'
    get_all_ts_files_url(url)
    download_ts_file_job()
    merge_all_ts_files()
