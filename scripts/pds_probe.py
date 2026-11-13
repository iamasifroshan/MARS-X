import rasterio

with rasterio.Env() as env:
    drivers = env.drivers()
    pds_matches = [k for k in drivers.keys() if any(x in k.upper() for x in ["PDS", "ISIS", "VICAR", "FITS"])]
    print("Found planetary drivers:", pds_matches)
