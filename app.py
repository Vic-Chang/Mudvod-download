import os
import requests
import m3u8


def download_ts_files(m3u8_url: str):
    playlist = m3u8.load(m3u8_url)
    temp_ts_folder = 'temp_ts'
    request = requests.session()
    if not os.path.exists(temp_ts_folder):
        os.mkdir(temp_ts_folder)
    for item in playlist.segments:
        file_name = os.path.basename(item.uri).split("?")[0]
        with request.get(item.uri, stream=True) as r:
            r.raise_for_status()
            with open(os.path.join(temp_ts_folder, file_name), 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)


if __name__ == '__main__':
    url = 'https://api.mudvod.tv/play/mud.m3u8/WEB/1.0?ce=6d657528bb2f55f7020392a18e350cf824adffef259330a6ba1509ff3621ce5f6927aa56b8c7e598847139ca75e82783b6088e5fedf034674fcb0a046246c5ad178e5e6828ef577327c0bb6e1a025b284b9245be9687d66a4d8a14fdbeb2ab4ed08f6bbaa395ee43e5d899e1efe860dcc889f8a570ac9bdc&pf=3&uk=ad552ef8019333d927d0aec6afb2d17d&rx=1898&expire=1657923827778&ip=118.163.56.205&sign=453eaa84866dd979a4a595663c154cec&_ts=1657898627778'
    download_ts_files(url)
