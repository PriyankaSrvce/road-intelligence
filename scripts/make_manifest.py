import re, csv, cv2, datetime as dt
from pathlib import Path

IST = dt.timedelta(hours=5, minutes=30)
GPX_START = dt.datetime(2026,10,15,3,24,35)   # UTC, from the GPX
GPX_END   = dt.datetime(2026,10,15,3,54,15)

rows = []
for f in sorted(Path("data/videos").glob("*.mp4")):
    m = re.match(r"(\d{8})_(\d{1,2})(\d{2})(\d{2})(AM|PM)", f.name)
    d, h, mi, s, ap = m.groups()
    h = int(h) % 12 + (12 if ap == "PM" else 0)
    local = dt.datetime.strptime(d, "%Y%m%d").replace(hour=h, minute=int(mi), second=int(s))
    utc = local - IST
    cap = cv2.VideoCapture(str(f))
    dur = cap.get(7) / cap.get(5)
    end = utc + dt.timedelta(seconds=dur)
    cov = max(0, (min(end, GPX_END) - max(utc, GPX_START)).total_seconds()) / dur
    rows.append([f.name, utc.strftime("%Y-%m-%dT%H:%M:%SZ"), round(dur,1),
                 "filename_gps_map_camera", f"gps_coverage={cov:.0%}"])
    print(rows[-1])

with open("data/clips_manifest.csv", "w", newline="") as o:
    w = csv.writer(o)
    w.writerow(["clip_file","gpx_start_utc","duration_s","sync_method","sync_note"])
    w.writerows(rows)