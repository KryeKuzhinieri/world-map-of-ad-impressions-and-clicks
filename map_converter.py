import shutil
import time
import webbrowser
from pathlib import Path

import branca
import folium
import pandas as pd
from PIL import Image
from folium.plugins import TimestampedGeoJson
from geopy.geocoders import Nominatim
from selenium import webdriver


class Map:
    """
    Class to create an animation from a folium map. It can generate html and gif files.
    """

    def __init__(self, html_filename="world_map.html", gif_filename="world_map.gif"):
        self.html_filename = html_filename
        self.gif_filename = gif_filename
        self._colormap = None
        self._features = None

    def to_gif(self, driver_option="Chrome", duration=500):
        """
        Takes the html file and converts it into a gif image.

        Parameters
        ----------
        driver_option : string
            Selenium browser driver. It accepts Chrome and Firefox as parameters.
        duration : int
            Amount of time the entire animation should take.

        Returns
        -------
        None
        """
        print("Converting screenshots to gif....")
        self._save_screenshots(driver_option)
        all_images = []
        for path in Path("tmp_dir").rglob('*.png'):
            all_images.append(Image.open(path))
        all_images[0].save(
            self.gif_filename,
            format="GIF",
            append_images=all_images[1:],
            save_all=True,
            duration=duration,
            loop=100
        )
        shutil.rmtree('tmp_dir', ignore_errors=True)
        print("Process completed!")

    def create_map(self, data, caption, normalize=False, date_column="date", value_column="clicks"):
        """
        Generates a TimestampedGeoJson animated folium map and saves the file as html.
        It opens the map on the browser after completion.

        Parameters
        ----------
        data : pandas dataframe
            A pandas dataframe. The dataset should contain a date column, location column, and a value column.
        caption : string
            The caption text next to the colormap.
        normalize : boolean
            If the column values are too large, it can display large circles on the map.
            You can set the value to True if you don't want this to happen.
        date_column : string
            The name of the date column.
        value_column : string
            The name of the value column.

        Returns
        -------
        A folium map object.
        """
        if normalize:
            data["clicks"] = (data["clicks"] - data["clicks"].mean()) / data["clicks"].std()
            data["clicks"] = data["clicks"].apply(lambda x: x if x > 1 else 1)
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
            self._features,
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
        self._colormap.add_to(world_map)
        world_map.save(self.html_filename)
        webbrowser.open(self.html_filename)
        return world_map

    def _create_colormap(self, column, caption):
        """
        Creates a colormap for the given data.

        Parameters
        ----------
        column : pandas array
            Pandas array with the values. It needs to calculate min and max values.
        caption : string
            Title of the map.
        Returns
        -------
        None
        """
        print("Creating colormap...")
        colormap = branca.colormap.LinearColormap(
            caption=caption,
            vmin=column.min(),
            vmax=column.max(),
            colors=["#b35549", "#a6ac24", "#1da976", "#1596ce"]
        )
        self._colormap = colormap

    def _create_geojson_features(self, data, caption, date_column="date", value_column="clicks"):
        """
        Generates features for the TimestamedGeoJson map. It saves the values into self._features.
        This function was taken from: https://www.linkedin.com/pulse/visualizing-nyc-bike-data-interactive-animated-maps-folium-toso/

        Parameters
        ----------
        data : pandas dataframe
            A pandas dataframe. The dataset should contain a date column, location column, and a value column.
        caption : string
            The caption text next to the colormap.
        date_column : string
            The name of the date column.
        value_column : string
            The name of the value column.

        Returns
        -------
        None
        """
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
                        'fillColor': self._colormap(row[value_column]),
                        'fillOpacity': 0.4,
                        'stroke': 'true',
                        'radius': row[value_column]
                    }
                }
            }
            features.append(feature)
        self._features = features

    def _save_screenshots(self, driver_option):
        """
        Runs selenium and takes a screenshot of the map every 1 second. It saves images into
        a tmp_dir as png. The images are then combined in the to_gif function.

        Parameters
        ----------
        driver_option : string
            Selenium browser driver. It accepts Chrome and Firefox as parameters.

        Returns
        -------
        None
        """
        print("Running selenium to capture screenshots....")
        options = getattr(webdriver, f"{driver_option}Options")()
        options.add_argument('window-size=1024x768')
        options.add_argument("--headless")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = getattr(webdriver, driver_option)(options=options)
        file_path = f"file://{Path().resolve()}/{self.html_filename}"
        driver.get(file_path)
        Path("tmp_dir").mkdir(parents=True, exist_ok=True)
        for i in range(30):
            time.sleep(1)
            driver.save_screenshot(f"{Path().resolve()}/tmp_dir/img{i}.png")
        driver.quit()

    @staticmethod
    def get_lat_long(data, location_column="country"):
        """
        Finds latitude and longitude for given locations and joins it to the dataset.

        Parameters
        ----------
        data : pandas dataframe
            A pandas dataframe. The dataset should contain a date column, location column, and a value column.
        location_column : string
            The name of the location column.

        Returns
        -------
        Pandas dataframe
        """
        geolocator = Nominatim(user_agent="Worldmap for Google Ads Clicks")
        lat, long = [], []
        unique_countries = data[location_column].unique()
        print(f"The dataset has {len(unique_countries)} locations. This takes some time! Fetching locations....")
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
