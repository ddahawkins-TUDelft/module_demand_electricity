import pandas as pd
from cleaning.combine_sources import combine_auxiliary_sources


def test_combine_auxiliary_sources_aligns_country_columns() -> None:
    index = pd.date_range("2020-01-01", periods=2, freq="h", tz="UTC")

    entsoe = pd.DataFrame({"GBR": [10.0, 11.0], "GRC": [20.0, 21.0]}, index=index)

    neso = pd.DataFrame({"GBR": [12.0, 13.0]}, index=index)

    combined, data_source, cleaning_method = combine_auxiliary_sources(
        {"entsoe_api": entsoe, "neso": neso}, priority=["neso", "entsoe_api"]
    )

    assert list(combined.columns) == ["GBR", "GRC"]

    assert combined["GBR"].tolist() == [12.0, 13.0]

    assert combined["GRC"].tolist() == [20.0, 21.0]

    assert data_source["GBR"].tolist() == ["neso", "neso"]

    assert data_source["GRC"].tolist() == ["entsoe_api", "entsoe_api"]

    assert cleaning_method.shape == combined.shape


def test_combine_auxiliary_sources_handles_empty_input() -> None:
    combined, data_source, cleaning_method = combine_auxiliary_sources(
        {}, priority=["entsoe_api", "neso", "opsd_api"]
    )

    assert combined.empty
    assert data_source.empty
    assert cleaning_method.empty
