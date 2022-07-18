import os
import requests
import m3u8
import queue
import threading


que = queue.Queue()
request = requests.session()

temp_ts_folder = 'temp_ts'
if not os.path.exists(temp_ts_folder):
    os.mkdir(temp_ts_folder)


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


if __name__ == '__main__':
    url = 'https://api.mudvod.tv/play/mud.m3u8/WEB/1.0?ce=6d657528bb2f55f7020392a18e350cf824adffef259330a6ba1509ff3621ce5f6927aa56b8c7e598847139ca75e82783b6088e5fedf034674fcb0a046246c5ad178e5e6828ef577327c0bb6e1a025b284b9245be9687d66a4d8a14fdbeb2ab4ed08f6bbaa395ee43e5d899e1efe860dcc889f8a570ac9bdc&pf=3&uk=ad552ef8019333d927d0aec6afb2d17d&rx=6056&expire=1658137275078&ip=118.163.56.205&sign=ab124fb2584cab1e4601055045be300f&_ts=1658112075078'
    # url = 'test.m3u8'
    get_all_ts_files_url(url)
    download_ts_file_job()
