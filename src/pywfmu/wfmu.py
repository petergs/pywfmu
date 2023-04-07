import requests
import http.cookiejar
from bs4 import BeautifulSoup


# text logo url - https://wfmu.org/wp-content/themes/wfmu-theme/img/non-retina/logo.png
# woof moo url - https://is2-ssl.mzstatic.com/image/thumb/Purple128/v4/e8/89/62/e88962f0-7068-769c-39c4-d8b70b40b1c9/contsched.oizxwbbg.lsr/1200x630bb.png
# alternate - https://fleamarketfunk.files.wordpress.com/2018/01/wfmu-logo-feature-image.jpg


STATUS_JSON_URL = "https://wfmu.org/wp-content/themes/wfmu-theme/status/main.json"
CURRENT_SHOW_JSON_URL = "https://wfmu.org/currentliveshows.php?json=1"
CAMPAIGN_JSON_URL = "https://pledge.wfmu.org/static/progress/campaign.json"
PLAYLIST_URL_BASE = "https://www.wfmu.org/playlists/shows/"
COMMENTS_XML_URL = "https://wfmu.org/current_playlist_xml.php?m=comments&c=1"
CURRENT_SHOW_XML_URL = "https://wfmu.org/currentliveshows.php?xml=1&c=1"
SCHEDULE_TODAY_XML_URL = "https://wfmu.org/playingtoday.php?xml=1&c=1"
SONGS_XML_URL = "https://wfmu.org/current_playlist_xml.php?m=songs"


class WFMUClient(object):
    def __init__(self):
        self.session = requests.Session()
        self._update_status()
        self.key = None

    @property
    def artist(self):
        self._update_status()
        return self._song["artist"]

    @property
    def title(self):
        self._update_status()
        return self._song["title"]

    @property
    def album(self):
        self._update_status()
        return self._song["album"]

    @property
    def playlist_id(self):
        self._update_status()
        return self._show["playlist_id"]

    @property
    def show(self):
        self._update_status()
        return self._show

    @property
    def song(self):
        self._update_status()
        return self._song

    def _update_status(self) -> None:
        r = requests.get(url=CURRENT_SHOW_JSON_URL)
        status = r.json()

        self._show = {
            "name": status["program"]["title_html"],
            "playlist_id": status["episode"]["id"],
            "playlist_link": status["episode"]["url"],
            "show_id": status["program"]["id"],
            # consider using SCHEDULE_TODAY_XML_URL for start+end since
            # CURRENT_SHOW_JSON_URL returns unpredictable text-based times
            "start": status["program"]["start_time_mmss"],
            "end": status["program"]["end_time_mmss"],
            "live": status["episode"]["live_indicator_flag"],
            "setbreak": status["segment"]["set_break_flag"],
        }
        self._song = {
            "title": status["segment"]["title_html"],
            "artist": status["segment"]["artist_html"],
            "album": status["segment"]["album_html"],
            "year": status["segment"]["year_html"],
            "record_label": status["segment"]["record_label_html"],
            "song_id": status["segment"]["song_fav_id"],
        }

        self._example = {"first": 1, "second": 2}

    # session and login
    def login(self, username: str, password: str) -> None:
        self.username = username
        payload = {
            "a": "login",
            "r": "https://wfmu.org/index.shtml",
        }
        r0 = self.session.get("https://wfmu.org/auth.php", params=payload)

        vals = self._extract_input_values(["__kfid"], r0.text)
        body = {
            "__kfid": vals["__kfid"],
            "a": "login_submit",
            "r": "https://wfmu.org/index.shtml",
            "sk": "",
            "u": username,
            "p": password,
            "login": "Sign in",
        }
        r1 = self.session.post("https://wfmu.org/auth.php", params=payload, data=body)
        self.key = vals["__kfid"]
        print(self.key)

    # playlist
    def get_playlist(self, playlist_id: int = -1) -> list:
        """
        Return a list of songs for playlist_id. It uses
        PLAYLIST_URL_BASE instead of SONGS_XML_URL since we can get return
        the playlist for both current & archive shows using PLAYLIST_URL_BASE.
        """
        if playlist_id == -1:
            playlist_id = self.playlist_id

        r = requests.get(f"{PLAYLIST_URL_BASE}{playlist_id}")
        soup = BeautifulSoup(r.text, "lxml-xml")
        songs = soup.find("span", id="songs")
        songs = [
            row
            for row in songs.find_all("tr")
            # exclude set_breaks and blank rows
            if row.find("td", "song col_artist") is not None
            and row.get("class") != "set_break_row"
        ]
        playlist = []
        song = {}
        for row in songs:
            # print(row)

            song["artist"] = row.find("td", "song col_artist").get_text().strip("\n")
            song["title"] = (
                row.find("td", "song col_song_title").font.get_text().strip("\n")
            )
            song["album"] = (
                row.find("td", "song col_album_title").get_text().strip("\n")
            )
            song["record_label"] = (
                row.find("td", "song col_record_label").get_text().strip("\n")
            )
            song["year"] = row.find("td", "song col_year").get_text().strip("\n")
            # THIS IS JANK
            # should write a helper function with some error handling
            song["song_id"] = (
                row.find("td", "song col_song_title")
                .find_all("span", "KDBFavIcon KDBsong")[1]
                .get("id")[8:]
            )
            # print(song)
            playlist.append(song)
            song = {}
        return playlist

    # comments
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
        self.key = vals["__kfid"]

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

    def get_comments(self) -> list:
        comments = []
        comment = {}
        r = self.session.get(COMMENTS_XML_URL)
        soup = BeautifulSoup(r.text, "lxml-xml")
        for c in soup.find_all("comment"):
            # using `find` instead of dot (.) notation due to name
            # collisions between bs4 properties and xml property names
            comment["id"] = c.get("id")
            comment["author"] = c.author.find("name").plaintext.get_text()
            comment["content"] = c.content.plaintext.get_text()
            if c.find("parent").get_text().strip("\n") == "":
                comment["parent"] = None
            else:
                comment["parent"] = {
                    "type": c.find("parent").find("type").get_text(),
                    "id": c.find("parent").id.get_text(),
                    "content": c.find("parent").plaintext.get_text(),
                }
            comments.append(comment)
            comment = {}

        return comments

    # favorites
    def favorite(self, playlist_id: int = -1, song_id: int = -1) -> None:
        if playlist_id == -1:
            playlist_id = self.playlist_id
            song_id = self.song["song_id"]
        self._favcon_toggle(playlist_id, song_id, state=0)

    def unfavorite(self, playlist_id: int = -1, song_id: int = -1) -> None:
        if playlist_id == -1:
            playlist_id = self.playlist_id
            song_id = self.song["song_id"]
        self._favcon_toggle(playlist_id, song_id, state=1)

    def _favcon_toggle(self, playlist_id: int, song_id: str, state) -> None:
        url = "https://www.wfmu.org/favcon.php?action=fav_icon_toggle"
        body = {
            "type": "song",
            "id": song_id,
            "state": state,
            "key": self.key,
            "myurl": f"http://wfmu.org/playlists/shows/{playlist_id}",
            "page_type": "playlist",
            "page_id": playlist_id,
        }
        r = self.session.post(url, data=body)
        pass

    def get_favorites(self) -> dict:
        # https://wfmu.org/auth.php?a=update_profile&panel_id=favorites
        pass

    # schedule
    def get_schedule_today(self) -> dict:
        pass

    # helpers
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
