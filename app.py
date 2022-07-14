import requests
import m3u8


def download_ts_files(m3u8_url:str):
    playlist = m3u8.load(m3u8_url)
    for item in playlist.segments:
        print(item.uri)


if __name__ == '__main__':
    url = 'https://api.mudvod.tv/play/mud.m3u8/WEB/1.0?ce=473c79abad38cea8e5598e3922847f34e907ddac030cff807f11a526b01c9322d431718768268810b7a7ca24b7650ae43ecb5aabfc4d6d1a0526829eb6f8a308ee66ab29ae403b818c1a61e641580195de6913d4bd00eda158e2125d164c55b179f9cdc1e5031693e1b23d4d75715c8afc04f4848945a8b1&pf=3&uk=50e4f5cc108d6dc0cc3b17c3ecb914d6&rx=14004&expire=1657817183948&ip=118.163.56.205&sign=757e7793aa29544292e5bac07b9d6d12&_ts=1657791983948'
    download_ts_files(url)
