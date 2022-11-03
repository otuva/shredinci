from bs4 import BeautifulSoup
from lipsum import lipsum
from random import randint
import urllib.parse
import requests
import logging
import base64
import pickle

USERNAME = "USERNAME"
PASSWORD = "PASSWORD"

_total_entry_number = None
_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
}


def set_logging():
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def get_entry_list(username: str, session: requests.Session):
    global _total_entry_number
    entry_list = []

    response = session.get("http://incisozluk.com.tr/u/{}/son-entry/?list=liste".format(username.replace(" ", "-")))

    soup = BeautifulSoup(response.text, 'html.parser')
    total_entry_number = soup.find("span", {"title": "toplam"}).text
    _total_entry_number = int(total_entry_number)
    print("Total entry number: {}".format(total_entry_number))

    if _total_entry_number == 0:
        print("There are no entries to delete")
        return entry_list

    entry_list_soup = soup.find("ul", {"class": "profil-baslik-list"})
    raw_entry_list = entry_list_soup.find_all("li", {"class": "nodisc"})

    for entry in raw_entry_list:
        slug = entry.find("a")["href"]
        entry_id = int(slug.split("/")[2])
        entry_list.append(entry_id)

    return entry_list


def purge_entry_list(username: str, session: requests.Session):
    entry_list = get_entry_list(username, session)
    for entry in entry_list:
        purge_entry(entry, session)

    print("\n===============================\nAll ({}) entries purged\n===============================\n".format(len(entry_list)))


def purge_entry(entry_id: int, session: requests.Session):
    print("--- Purging entry --- {}".format(entry_id))
    override_entry_content(entry_id, session)
    delete_entry(entry_id, session)
    print("--- Purged entry --- {}\n".format(entry_id))


def override_entry_content(entry_id: int, session: requests.Session):
    content = lipsum[str(randint(0, len(lipsum) - 1))]
    print("Overriding entry {} with filler text".format(entry_id))
    edit_entry(entry_id, content, session)


def delete_entry(entry_id: int, session: requests.Session):
    print("Deleting entry {}".format(entry_id))

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/105.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'http://incisozluk.com.tr',
        'Connection': 'keep-alive',
        'Referer': 'http://incisozluk.com.tr/e/{}/'.format(entry_id),
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    params = {
        'a': 'yenig',
        'na': 'entry',
        'na2': 'sil',
    }

    data = {
        'entry_id': str(entry_id),
    }

    response = session.post('http://incisozluk.com.tr/ax/', params=params, headers=headers, data=data)
    assert response.status_code == 200 and response.text.find("\"durum\":\"success\"") != -1, "Deletion failed"


def edit_entry(entry_id: int, content: str, session: requests.Session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'multipart/form-data; boundary=---------------------------13936099111585919444441087403',
        'Origin': 'http://incisozluk.com.tr',
        'Connection': 'keep-alive',
        'Referer': 'http://incisozluk.com.tr/e/{}/?tab=duzenle'.format(entry_id),
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    params = {
        'a': 'yenig',
        'na': 'entry',
        'na2': 'entry_guncelle',
    }

    data = '-----------------------------13936099111585919444441087403\r\n' \
           'Content-Disposition: form-data; name="entry"\r\n' \
           '\r\n' \
           f'{content}\r\n' \
           '-----------------------------13936099111585919444441087403\r\n' \
           'Content-Disposition: form-data; name="videolocal"; filename=""\r\n' \
           'Content-Type: application/octet-stream\r\n' \
           '\r\n' \
           '-----------------------------13936099111585919444441087403\r\n' \
           'Content-Disposition: form-data; name="entry_id"\r\n' \
           '\r\n' \
           f'{entry_id}\r\n' \
           '-----------------------------13936099111585919444441087403--\r\n'

    response = session.post('http://incisozluk.com.tr/ax/', params=params, headers=headers, data=data)
    assert response.status_code == 200 and response.text.find("\"durum\":\"success\"") != -1, "Edit failed"


def login(username: str, password: str, session: requests.Session):
    login_page = session.get("http://www.incisozluk.com.tr/y/login/")
    login_page.encoding = login_page.apparent_encoding

    login_page_soup = BeautifulSoup(login_page.text, 'html.parser')
    rote = login_page_soup.find("input", {"name": "rote"})["value"]
    rote = base64.b64encode(base64.b64decode(rote) + b"www.incisozluk.com.tr").decode("utf-8")

    headers = _headers.copy()
    headers.update({
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.incisozluk.com.tr/y/login/',
    })

    params = {
        'sa': 'login',
        'ne': 'yap',
    }

    login_data = 'kuladi={username}&sifre={password}&gonder=login&rote={rote}&giris_ref=https%3A%2F%2Fwww.incisozluk.com.tr%2F'.format(
        username=urllib.parse.quote(username), password=urllib.parse.quote(password), rote=rote)

    response = session.post('http://www.incisozluk.com.tr/index.php', params=params, headers=headers,
                            data=login_data)

    response.encoding = response.apparent_encoding
    assert response.text.find("bilginin peşinden") != -1, "Login failed"


def main():
    # set_logging()

    # check if we have a session file
    try:
        with open("session.pickle", "rb") as f:
            session = pickle.load(f)
            print("Loaded session from pickle file")
    except FileNotFoundError:
        # Create a session in main and pass it to other functions. (for serialization)
        print("Creating new session")
        session = requests.Session()
        session.verify = False
        session.headers.update(_headers)
        login(USERNAME, PASSWORD, session)
        # Save session to file
        with open("session.pickle", "wb") as f:
            pickle.dump(session, f)

    while True:
        purge_entry_list(USERNAME, session)
        if _total_entry_number == 0:
            break


if __name__ == "__main__":
    main()
