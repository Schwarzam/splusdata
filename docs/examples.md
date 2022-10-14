
Connecting to splus user.
```
import splusdata
conn = splusdata.connect('user', 'pass') ## from splus.cloud
```

<br>

Getting twelve band images.
```
conn.twelve_band_img(43.3559, -0.2322, radius=3000, noise=0.15, saturation=0.15)
```
<br>
Getting three band fast images.
```
conn.get_img(43.3559, -0.2322, 200, R="I", G="R", B="G", stretch=0.5, Q=5)
```
<br>

Getting FITS image cuts.
```
conn.get_cut(0.4, 0.7, 1500, 'R')
```

<br>

Async query on splus.cloud TAP system.
```
conn.query('select id, ra, dec from dr2.detection_image where ra + dec > 200')
```


