import pandas as pd
from pywindsorai.client import Client

from map_converter import Map


def main():
    # Fetch dataset
    client = Client(api_key="your-key")
    request = client.connectors(
        date_from="2022-10-01",
        date_to="2022-11-01",
        fields=["date", "country", "source", "campaign", "clicks"],
        connector="google_ads"
    )
    dataset = pd.DataFrame(request["data"])

    # Create map
    generator = Map()
    # If dataset does not have latitude and longitude, find them.
    dataset = generator.get_lat_long(dataset, location_column="country")
    # dataset = pd.read_csv("temp.csv", sep="\t")

    # Create HTML map
    generator.create_map(
        data=dataset,
        caption="Google Ads Clicks By Country (October 2022)",
        normalize=True
    )
    # Convert map to gif.
    generator.to_gif(driver_option="Chrome")


if __name__ == "__main__":
    main()
