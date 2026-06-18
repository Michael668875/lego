from app import create_app
import requests
from base64 import b64encode
import os
from dotenv import load_dotenv
import time
import json

load_dotenv()
app = create_app()

CLIENT_ID = os.environ.get("EBAY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID")
CATEGORY_ID = "183446"

def get_token():
    auth = b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    url = "https://api.ebay.com/identity/v1/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_paginated_summaries(query="lego", limit=200):
    token = get_token()

    marketplaces = {
        "EBAY_US": {"country": "US", "max_items": 1000},
        "EBAY_AU": {"country": "AU", "max_items": 1000},
        "EBAY_GB": {"country": "GB", "max_items": 1000},
        "EBAY_DE": {"country": "DE", "max_items": 1000}
    }

    all_items = []

    for market, config in marketplaces.items():

        country_code = config["country"]
        maximum_items = config["max_items"]

        offset = 0
        market_items = []

        while len(market_items) < maximum_items:

            url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

            headers = {
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": market,
                "X-EBAY-C-ENDUSERCTX": f"affiliateCampaignId={CAMPAIGN_ID}"
            }

            params = {
                "q": query,
                "category_ids": CATEGORY_ID,
                "limit": limit,
                "offset": offset,
                "fieldgroups": "EXTENDED",
               # "sort": "newlyListed", # this may be hurting fetch. rely on ebay's default sort instead
                "filter": f"conditionIds:{{1000|1500|2000|2500|3000}},"
                        f"buyingOptions:{{FIXED_PRICE}},"
                        f"itemLocationCountry:{country_code}"
            }

            try:
                print(f"{market}: page {offset // limit + 1}")
                resp = requests.get(url, headers=headers, params=params)
                resp.raise_for_status()

                """
                data = resp.json()  # added for debug and to get total values

                print( # find out total fetchable values
                    f"{market}: total={data.get('total', 'unknown')} "
                    f"offset={offset}"
                )
                """

                items = resp.json().get("itemSummaries", [])

                if not items:
                    break

                filtered_items = []

                for item in items:
                    item_country = item.get("itemLocation", {}).get("country")

                    if item_country != country_code:
                        continue

                    item["marketplace_id"] = market
                    item["marketplace_country"] = market.split("_", 1)[1]
                    filtered_items.append(item)

                remaining = maximum_items - len(market_items)
                market_items.extend(filtered_items[:remaining])

                offset += limit

                # stop if last page
                if len(items) < limit:
                    break

                time.sleep(0.2)

            except requests.RequestException as e:
                print(f"Failed fetching {market} page {offset // limit + 1}: {e}")
                break

        print(f"{market}: fetched {len(market_items)} items")

        all_items.extend(market_items)

    unique = {item["itemId"]: item for item in all_items}
    #with open("fetch_data.txt", "w") as f:
    #    json.dump(list(unique.values()), f, indent=2)

    return list(unique.values())

#get_summaries()