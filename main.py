import pandas as pd
import branca
import folium
from folium.plugins import TimestampedGeoJson
from geopy.geocoders import Nominatim
from pywindsorai.client import Client
from selenium import webdriver
import time
from PIL import Image
from pathlib import Path

API_KEY = "my-key"
geolocator = Nominatim(user_agent="Worldmap for Google Ads Clicks")


class Map:

    def __init__(self, key):
        self.key = key
        self.html_filename = "world_map.html"
        self.colormap = None
        self.features = None

    def get_data(self, **kwargs):
        print("Reading data....")
        client = Client(api_key=self.key)
        request = client.connectors(**kwargs)
        if client.status_code != 200:
            raise Exception(request)
        data = pd.DataFrame(request["data"])
        print(f"The dataset has {len(data)} points.")
        return data

    @staticmethod
    def get_lat_long(data, location_column="country"):
        lat, long = [], []
        unique_countries = data[location_column].unique()
        print(f"The dataset has {len(unique_countries)} locations. Fetching them....")
        for c in unique_countries:
            location = geolocator.geocode(c)
            if location:
                lat.append(location.latitude)
                long.append(location.longitude)
            else:
                lat.append(float("Nan"))
                long.append(float("Nan"))
        lat_long_data = pd.DataFrame(
            data={
                location_column: unique_countries,
                "latitude": lat,
                "longitude": long
            }
        )
        data = data.merge(lat_long_data, on=location_column, how="left")
        print("Data fetched successfully!")
        return data

    def _create_colormap(self, column, caption):
        print("Creating colormap...")
        colormap = branca.colormap.LinearColormap(
            caption=caption,
            vmin=column.min(),
            vmax=column.max(),
            colors=["#b35549", "#a6ac24", "#1da976", "#1596ce"]
        )
        self.colormap = colormap

    def _create_geojson_features(self, data, caption, date_column="date", value_column="clicks"):
        self._create_colormap(data[value_column], caption)
        print("Generating geo features...")
        features = []
        for _, row in data.iterrows():
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [row['longitude'], row['latitude']]
                },
                'properties': {
                    'time': pd.to_datetime(row[date_column]).__str__(),
                    'style': {'color': ''},
                    'icon': 'circle',
                    'tooltip': row["country"],
                    'iconstyle': {
                        'fillColor': self.colormap(row[value_column]),
                        'fillOpacity': 0.4,
                        'stroke': 'true',
                        'radius': row[value_column]
                    }
                }
            }
            features.append(feature)
        self.features = features

    def create_map(self, data, caption, normalize=False, date_column="date", value_column="clicks"):
        if normalize:
            dataset["clicks"] = (dataset["clicks"] - dataset["clicks"].mean()) / dataset["clicks"].std()
            dataset["clicks"] = dataset["clicks"].apply(lambda x: x if x > 1 else 1)
        self._create_geojson_features(data, caption, date_column, value_column)
        print("creating map....")
        world_map = folium.Map(
            tiles="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a '
                 'href="https://carto.com/attributions">CARTO</a>',
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False,
            doubleClickZoom=False,
            attributionControl=False,
            location=[0, 30],
            zoom_start=1.5,
        )

        TimestampedGeoJson(
            self.features,
            period='P1D',
            duration='P1D',
            transition_time=1000,
            auto_play=True,

        ).add_to(world_map)

        html_to_insert = """
            <style>
                .caption {
                    fill: white !important; 
                }

                .tick {
                    fill: white !important;
                }

                .leaflet-bar {
                    display: none !important;
                }

            </style>
        """
        world_map.get_root().header.add_child(folium.Element(html_to_insert))
        self.colormap.add_to(world_map)
        world_map.save(self.html_filename)
        return world_map

    def _save_screenshots(self, driver_option):
        print("Running selenium to capture screenshots....")
        options = getattr(webdriver, f"{driver_option}Options")()
        options.add_argument('window-size=1024x768')
        options.add_argument("--headless")
        driver = getattr(webdriver, driver_option)(options=options)
        file_path = f"file://{Path().resolve()}/{self.html_filename}"
        driver.get(file_path)
        for i in range(30):
            time.sleep(1)
            driver.save_screenshot(f"{Path().resolve()}/tmp_folder/img{i}.png")
        driver.quit()

    def to_gif(self, driver_option="Firefox"):
        print("Converting screenshots to gif....")
        self._save_screenshots(driver_option)
        all_images = []
        for path in Path("tmp_folder").rglob('*.png'):
            all_images.append(Image.open(path))
        all_images[0].save(
            "world_map.gif",
            format="GIF",
            append_images=all_images[1:],
            save_all=True,
            duration=1000,
            loop=100
        )


generator = Map(key=API_KEY)
dataset = generator.get_data(
    date_from="2022-10-01",
    date_to="2022-11-01",
    fields=["date", "country", "source", "campaign", "clicks"],
    connector="google_ads"
)
dataset = generator.get_lat_long(dataset, location_column="country")
m = generator.create_map(data=dataset, caption="Google Ads Clicks By Country (October 2022)")
generator.to_gif(driver_option="Chrome")
