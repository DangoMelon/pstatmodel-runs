#%%
import pickle

import numpy as np
import pandas as pd
import xarray as xr

#%%
predictors = pd.read_excel("Predictores_IniMay.xlsx", index_col=[0])

pisco = (
    xr.open_dataset("/data/users/grivera/PISCOPrecv2p1.nc", decode_times=False)
    .rename({"X": "lon", "Y": "lat", "T": "time"})
    .load()
)
pisco.time.attrs["calendar"] = "360_day"
pisco = xr.decode_cf(pisco).Prec
pisco = pisco.sel(time=slice("1981-10-01", "2016-05-01"))

months_index = pisco.groupby("time.month").groups

#%%
full_model = {}
for mnum, mindex in months_index.items():
    try:
        with open(
            f"/data/users/grivera/pstatmodel_data/RUNS/MAY/model_may.{mnum:02d}.pickle",
            "rb",
        ) as handle:
            full_model[mnum] = pickle.load(handle)
        print(f"Succesfully read model for month number {mnum}", flush=True)
    except:
        print(f"Couldn't find model for month number {mnum}", flush=True)

#%%
lats = pisco.lat
lons = pisco.lon

fcst_data = xr.DataArray(
    np.nan,
    coords=[
        (
            "time",
            pd.date_range("1981-10", "2022-05", freq="MS") + pd.DateOffset(days=14),
        ),
        ("lat", lats),
        ("lon", lons),
    ],
)

#%%

pred_groups = fcst_data.groupby("time.month").groups
new_pred = predictors.loc[1981:].copy()
new_pred["const"] = 1

#%%

for mnum, nmodel in full_model.items():

    print(f"\nStarting model month number: {mnum}", flush=True)

    for (lat, lon), (pixel_vars, pixel_model, thresh_in) in nmodel:
        if not isinstance(pixel_model, float) and len(pixel_vars) != 0:
            sel_time = fcst_data.time.isel(time=pred_groups[mnum]).data
            fcst_data.loc[dict(lat=lat, lon=lon, time=sel_time)] = pixel_model.predict(
                new_pred[pixel_model.params.index]
            )
    print(f"Finished model month number: {mnum}\n")

#%%
fcst_data = fcst_data.dropna(dim="time", how="all")

fcst_data.name = "fcst_data"
fcst_data.to_netcdf("/data/users/grivera/pstatmodel_data/RUNS/MAY/Data/fcst_data.nc")