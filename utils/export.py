"""
Export scraped data to CSV / Excel / JSON
"""

import os
import json
import pandas as pd
import config


def _make_df(businesses: list[dict]) -> pd.DataFrame:
    columns = [
        "name", "category", "phone", "email", "address",
        "website", "instagram", "rating", "reviews",
        "maps_url", "source",
    ]
    df = pd.DataFrame(businesses)
    # ensure all columns exist
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def export_csv(businesses: list[dict], filename: str = "leads.csv") -> str:
    path = os.path.join(config.OUTPUT_DIR, filename)
    df = _make_df(businesses)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def export_excel(businesses: list[dict], filename: str = "leads.xlsx") -> str:
    path = os.path.join(config.OUTPUT_DIR, filename)
    df = _make_df(businesses)
    df.to_excel(path, index=False, engine="openpyxl", sheet_name="Leads")
    return path


def export_json(businesses: list[dict], filename: str = "leads.json") -> str:
    path = os.path.join(config.OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(businesses, f, indent=2, ensure_ascii=False)
    return path
