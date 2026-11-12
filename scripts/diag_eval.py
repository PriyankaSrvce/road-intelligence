import cv2, glob, statistics as st
from pathlib import Path
from PIL import Image
D = Path("data/sample_dataset_yolo")
imgs = sorted((D/"images").glob("*.jpg"))
print("n images:", len(imgs))
sizes, orient = {}, {}
for p in imgs:
    im = Image.open(p)
    sizes[im.size] = sizes.get(im.size, 0) + 1
    o = im.getexif().get(274, 1)          # EXIF orientation
    orient[o] = orient.get(o, 0) + 1
print("image sizes (w,h):count ->", sizes)
print("EXIF orientation (1=normal):count ->", orient)
w, h = [], []
for f in (D/"labels").glob("*.txt"):
    for l in f.read_text().splitlines():
        p = l.split()
        if len(p) >= 5:
            w.append(float(p[3])); h.append(float(p[4]))
print(f"GT box size (normalised): median w={st.median(w):.3f} h={st.median(h):.3f}, min w={min(w):.4f}")
# draw GT on 6 images so you can eyeball them
Path("docs/figures/diag").mkdir(parents=True, exist_ok=True)
for p in imgs[:6]:
    im = cv2.imread(str(p)); H, W = im.shape[:2]
    for l in (D/"labels"/f"{p.stem}.txt").read_text().splitlines():
        c, cx, cy, bw, bh = l.split()[:5]
        cx, cy, bw, bh = float(cx)*W, float(cy)*H, float(bw)*W, float(bh)*H
        cv2.rectangle(im, (int(cx-bw/2), int(cy-bh/2)), (int(cx+bw/2), int(cy+bh/2)), (0,255,0), max(3, W//300))
    cv2.imwrite(f"docs/figures/diag/gt_{p.stem[-8:]}.jpg", cv2.resize(im, (W*800//max(W,H), H*800//max(W,H))))
print("wrote GT overlays to docs/figures/diag")
