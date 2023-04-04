# pywfmu
> A python library for interacting with wfmu.org

This is still very much a WIP.

## Quickstart
Get the current live show and song
```
>>> from pywfmu import WFMUClient
>>> woofmoo = WFMUClient()
>>> woofmoo.update_status() 
>>> woofmoo.show
{'name': "Daniel Blumin's show", 'playlist_id': '126345', 'playlist_link': 'https://www.wfmu.org/playlists/shows/126345'}
>>> woofmoo.song
{'title': 'Kizmiaz', 'artist': 'Don & Francoiz', 'album': 'Cover Songs in Inferno'}
```

## Acknowledgments
- WFMU.org is powered by KenzoDB, by Ken Garson (http://kenzodb.com).
- Thanks to [BurpSuite](https://portswigger.net/burp) and [Charles](https://www.charlesproxy.com/) for making this project much easier.

