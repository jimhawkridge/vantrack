import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('position.csv', delimiter='\t', parse_dates=['timestamp'])
df = df[
    (df['timestamp'] >= datetime(2016, 7, 31)) &
    (df['timestamp'] <= datetime(2016, 8, 16))
]

df['isotime'] = df['timestamp'].map(lambda ts: ts.isoformat())
df = df[df['isotime'] != '2013-11-11T00:00:00']

df = df.sort_values('timestamp')
df['longdiff'] = df['long'].diff().abs()
df['latdiff'] = df['lat'].diff().abs()
df = df[(df['longdiff'] > 0.0005) | (df['latdiff'] > 0.0005)]
segs = df.groupby((df['timestamp'].diff() > timedelta(minutes=2)).apply(lambda x: 1 if x else 0).cumsum())

def format_pts(pts):
    return ('<trkpt lat="{0.lat}" lon="{0.long}"><time>{0.isotime}</time></trkpt>\n'.format(p[1]) for p in pts)

f = open('trk.gpx', 'w')
f.write("""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.0">
    <name>A track</name>
    <trk>
       <name>Where we went</name>
       <number>1</number>
""")
for segname, seg in segs:
    f.write("<trkseg>\n")
    segpts = format_pts(seg.iterrows())
    f.writelines(segpts)
    f.write("</trkseg>\n")
f.write("""
    </trk>
</gpx>
""")
f.close()

