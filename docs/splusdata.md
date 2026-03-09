# splusdata python package

The **splusdata** package relies on the **adss** package since it uses the same engine.  
This means you can connect to the other mirrors with splusdata just as you would with splus.cloud.  

To install, simply run:

```bash
pip install splusdata --upgrade
```

## Quick start

(It’s always a good idea to check the available parameters for each function in your editor.
For example, in VS Code you can hover the mouse over a function to see its signature.
Everything here is designed to be as self-explanatory as possible.)

First, you need to authenticate using the Core class.
It will hold your authentication token for all requests.
This is also important for handling any special permissions your account may have.

```python
import splusdata

conn = splusdata.Core()  # will prompt for username/password if not provided
# Or:
# conn = splusdata.Core(username="user@example.com", password="•••••")
```

## Images

You can begin by checking what we call collections (the available data releases):

```python
releases = conn.check_available_images_releases()
print(releases)  # e.g., ["dr4", "dr5", "dr6"]
```

To get a full fits frame:

### Full field FITS image
```python
# Science frame
hdu_list = conn.field_frame(field="SPLUS-n01s10", band="R", data_release="dr4")
print(hdu_list.info())

# Optionally save directly:
# hdu_list = conn.field_frame("SPLUS-n01s10", "R", outfile="n01s10_R.fits", data_release="dr4")

# Weight map
w_hdu_list = conn.field_frame("SPLUS-n01s10", "R", weight=True, data_release="dr4")
```

### Create a FITS stamp (cutout)

Stamps are created in real time and correspond to the stamp tool on the website.

By coordinates:
```python
stamp = conn.stamp(
    ra=10.1234, 
    dec=-2.3456, 
    size=300, 
    band="I", 
    size_unit="pixels", 
    data_release="dr4"
)
data = stamp[1].data
```

By field/object context:
```python
stamp = conn.stamp(
    ra=10.1234, 
    dec=-2.3456, 
    size=20, 
    band="F660",
    field_name="SPLUS-n01s10", 
    size_unit="arcsec", 
    data_release="dr4"
)
```

### Lupton RGB composite

Creates an RGB image from selected filters in real time. Returns a PIL.Image.Image object.

```python
rgb = conn.lupton_rgb(
    ra=10.1234, dec=-2.3456, size=600,
    R="I", G="R", B="G",
    Q=8, stretch=3,
    data_release="dr4"
)
rgb.save("rgb_lupton.png")
```

### Trilogy RGB composite
```python
tri = conn.trilogy_image(
    ra=10.1234, dec=-2.3456, size=600,
    R=["R","I","F861","Z"], G=["G","F515","F660"], B=["U","F378","F395","F410","F430"],
    noiselum=0.15, satpercent=0.15, colorsatfac=2,
    data_release="dr4"
)
tri.save("rgb_trilogy.png")
```


## Run a query (with optional upload)
Plain query:
```python
result = conn.query("SELECT 1 AS ok")
print(result)
```

With upload:
```python
import pandas as pd
df = pd.DataFrame({"ra":[10.1, 10.2], "dec":[-2.3, -2.4]})
res = conn.query(
    query="""
        SELECT *
        FROM upload.{input_your_name}
    """,
    table_upload=df,
    table_name={input_your_name}
)
```

## Zero points (DR6) and calibrated stamps
Fetch the JSON model:
```python
zp_model = conn.get_zp_file(field="SPLUS-n01s10", band="R", data_release="dr6")
```

Evaluate zp at a coordinate:
```python
zp = conn.get_zp(field="SPLUS-n01s10", band="R", ra=10.1234, dec=-2.3456)
print("zp =", zp)
```

or you may also pass arrays of coordinates:
```python
import numpy as np

ras = np.random.uniform(150, 150.5, 10000)
decs = np.random.uniform(-24, -23.5, 10000)

zps = conn.get_zp(field="HYDRA-0011", band="R", ra=ras, dec=decs)
```

Create a calibrated cutout and save it:
```python
calib_hdu = conn.calibrated_stamp(
    ra=10.1234, dec=-2.3456, size=300, band="R",
    outfile="calibrated_stamp_R.fits",
    data_release="dr6"
)
```

## Error handling
Wrap calls with `try/except` to gracefully handle missing files or invalid inputs:
```python
from splusdata import SplusdataError

try:
    hdu = conn.field_frame("SPLUS-nXXsYY", "R", data_release="dr4")
except SplusdataError as e:
    print("S-PLUS error:", e)
```

## Tips & notes
- **Field name normalization:** `get_file_metadata` will retry once with `-` and `_` swapped if the field isn’t found.
- **Patterns:** Many collections expose helpful `patterns` such as science vs. weight images; you can pass `"weight"` where applicable.
- **Units:** Stamps accept `size_unit="pixels"` or `"arcsec"`. Choose based on your workflow.
- **Headers:** Stamps typically carry headers with `FIELD`, `FILTER`, etc. The calibration step expects them.
- **I/O:** You can pass `outfile` to let the server write files directly to disk, and you can also manually save images returned as `PIL.Image.Image`.
