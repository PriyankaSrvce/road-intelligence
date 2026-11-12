import re, sys, datetime as dt
from pathlib import Path
clip, sec = sys.argv[1], float(sys.argv[2])
m = re.match(r"(\d{8})_(\d{1,2})(\d{2})(\d{2})(AM|PM)", clip)
d,h,mi,s,ap = m.groups(); h = int(h)%12 + (12 if ap=="PM" else 0)
t0 = dt.datetime.strptime(d,"%Y%m%d").replace(hour=h,minute=int(mi),second=int(s)) - dt.timedelta(hours=5,minutes=30) + dt.timedelta(seconds=sec)
g = open("data/gps/20261015-085435_morning_college.gpx").read()
pts = re.findall(r'<trkpt lat="([-\d.]+)" lon="([-\d.]+)">.*?<time>(.*?)</time><speed>(.*?)</speed>', g, re.S)
for lat,lon,t,sp in pts:
    if abs((dt.datetime.strptime(t,"%Y-%m-%dT%H:%M:%SZ")-t0).total_seconds()) <= 2:
        print(t, lat, lon, f"speed={float(sp)*3.6:.0f} km/h")
