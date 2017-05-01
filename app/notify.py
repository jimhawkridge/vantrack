import requests

from geocode import reverse_geocode
import settings


def pushover(title, message, url_title, url, priority):
    payload = {
        'token': settings.PUSHOVER_TOKEN,
        'user': settings.PUSHOVER_USER,
        'title': title,
        'url': url,
        'url_title': url_title,
        'message': message,
        'priority': priority
    }
    if priority == 2:
        payload['expire'] = 8 * 60 * 60
        payload['retry'] = 60

    resp = requests.post('https://api.pushover.net/1/messages.json', payload)
    if resp.status_code != 200:
        print('** Error notifying **')
        print(resp.text)


def notify_position(lat, lon, key):
    address = reverse_geocode(lat, lon, key)
    pushover(
        'Van Position',
        'The van is currently at {}.'.format(address),
        'Location',
        'geo:{},{}'.format(lat, lon),
        -1
    )
