import requests
import http.cookiejar
from bs4 import BeautifulSoup


# text logo url - https://wfmu.org/wp-content/themes/wfmu-theme/img/non-retina/logo.png
# woof moo url - https://is2-ssl.mzstatic.com/image/thumb/Purple128/v4/e8/89/62/e88962f0-7068-769c-39c4-d8b70b40b1c9/contsched.oizxwbbg.lsr/1200x630bb.png
# alternate - https://fleamarketfunk.files.wordpress.com/2018/01/wfmu-logo-feature-image.jpg


STATUS_JSON_URL = "https://wfmu.org/wp-content/themes/wfmu-theme/status/main.json"
CAMPAIGN_JSON_URL = "https://pledge.wfmu.org/static/progress/campaign.json"
PLAYLIST_URL_BASE = "https://www.wfmu.org/playlists/shows/"
COMMENTS_XML_URL = "http://wfmu.org/current_playlist_xml.php?m=comments&c=1"


class WFMUClient(object):
    def __init__(
        self,
        cookies_file="cookies.txt",
    ):
        self.session = requests.Session()
        # jar = http.cookiejar.FileCookieJar(cookies_file)
        # self.session.cookies = jar
        self.update_status()

    @property
    def artist(self):
        return self.song["artist"]

    @property
    def title(self):
        return self.title["title"]

    @property
    def album(self):
        return self.song["album"]

    def login(self, username: str, password: str) -> None:
        self.username = username
        payload = {
            "a": "login",
            "r": "https://wfmu.org/index.shtml",
        }
        r0 = self.session.get("https://wfmu.org/auth.php", params=payload)

        soup = BeautifulSoup(r0.text, features="lxml")
        inputs = soup.find_all("input")
        for inp in inputs:
            if inp.get("name") == "__kfid":
                kfid = inp.get("value")

        body = {
            "__kfid": kfid,
            "a": "login_submit",
            "r": "https://wfmu.org/index.shtml",
            "sk": "",
            "u": username,
            "p": password,
            "login": "Sign in",
        }
        r1 = self.session.post("https://wfmu.org/auth.php", params=payload, data=body)

    def update_status(self) -> None:
        r = requests.get(url=STATUS_JSON_URL)
        status = r.json()

        self.show = {
            "name": status["show"],
            "playlist_id": status["playlist"]["@attributes"]["id"],
            "playlist_link": f"{PLAYLIST_URL_BASE}{status['playlist']['@attributes']['id']}",
        }
        self.song = {
            "title": status["title"],
            "artist": status["artist"],
            "album": status["album"],
        }
        self.live = (
            True if status["liveIndicator"]["@attributes"]["flag"] == "1" else False
        )
        self.setbreak = (
            True if status["setBreak"]["@attributes"]["flag"] == "1" else False
        )

    def comment(self, comment: str) -> None:
        r0 = self.session.get(self.show["playlist_link"])
        e = self._extract_input_values(["e"], r0.text)
        body = {
            "a": self.username,
            "c": comment,
            "d": "Post+!",  # this originates from `playlist_link`, but the WFMU iOS app uses `iphone`
            "e": e["e"],  # post token
            "f": "",  # reply to song
            "g": "",  # reply to comment
        }
        r1 = self.session.post("https://wfmu.org/playlistcommentpost.php", data=body)

        vals = self._extract_input_values(["c", "pe", "__kfid"], r1.text)
        body = {
            "__kfid": vals["__kfid"],
            "c": vals["c"],
            "pa": self.username,
            "pb": "",
            "pc": comment,  # this value doesn't appear to matter
            "pe": vals["pe"],
            "pf": "",
            "pg": "",
            "b": "POST THAT NOW!",
        }
        r2 = self.session.post(
            "https://wfmu.org/playlistcommentpost.php", params={"p": 1}, data=body
        )

    def _extract_input_values(self, names: list, html: str) -> dict:
        """
        Extract values used for some strange form validation on wfmu.org.
        `names` is a list of the required <input> tag names
        `html` is the text of the the request page containing the values

        Returns a dictionary of name value pairs
        """
        soup = BeautifulSoup(html, features="lxml")
        inputs = soup.find_all("input")
        vals = {}
        for inp in inputs:
            name = inp.get("name")
            if name in names:
                vals[name] = inp.get("value")

        return vals
