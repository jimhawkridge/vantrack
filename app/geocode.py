from collections import defaultdict
import requests
import settings


caches = {}


def reverse_geocode(lat, lon, key):
    cache_lat, cache_lon, cache_result = caches.get(key, (0, 0, 'Unknown'))
    lat_dist = abs(cache_lat - lat)
    lon_dist = abs(cache_lon - lon)
    dist = (lat_dist ** 2 + lon_dist ** 2) ** 0.5
    if dist < settings.GEOCODE_THRESHHOLD:
        print(dist, ' < ', settings.GEOCODE_THRESHHOLD, '. No re-geocode')
        return cache_result

    print(dist, ' >= ', settings.GEOCODE_THRESHHOLD, '. Need to re-geocode')

    resp = requests.get(
        'http://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}&zoom=16&addressdetails=1'.format(lat, lon)
    )
    if resp.status_code != 200:
        return 'Unknown'

    data = resp.json()
    address = defaultdict(str, data['address'])
    result = '{road}, {suburb}, {city}'.format(**address)
    result = result.replace(' CP', '')
    caches[key] = (lat, lon, result)
    return result
