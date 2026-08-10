"""Schemas for key files."""

# ruff: noqa: UP007
import pandas as pd
import yaml
from pandera.pandas import DataFrameModel, Field
from pandera.typing.geopandas import GeoSeries
from pandera.typing.pandas import Series


def read_yaml(path):
    """Read a YAML file."""
    with open(path) as file:
        return yaml.safe_load(file)


class LoadENTSOE(DataFrameModel):
    class Config:
        coerce = True
        strict = False

    region: Series[str]
    "2-letter country code."
    variable: Series[str]
    "Variable."
    attribute: Series[str]
    "Attribute."
    utc_timestamp: Series[pd.Timestamp]
    "UTC timestamp."
    data: Series[float]
    "Load data."


class Shapes(DataFrameModel):
    class Config:
        coerce = True
        strict = False

    shape_id: Series[str]
    "Shape ID."
    country_id: Series[str]
    "Country ID."
    shape_class: Series[str] = Field(isin=["land", "maritime"])
    "Shape class."
    geometry: GeoSeries
    "Geometry."
