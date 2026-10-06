from data_observatory.metadata import DataStatus, Metadata, with_date_coverage, with_status


def _sample_meta(status=DataStatus.OFFICIAL) -> Metadata:
    return Metadata(
        indicator="GDP (current US$)",
        source="World Development Indicators — NY.GDP.MKTP.CD",
        provider="World Bank",
        url="https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD",
        definition="Gross Domestic Product at purchaser's prices.",
        unit="current US$",
        frequency="annual",
        date_coverage="",
        transformations=("none",),
        limitations="Current-US$ GDP mixes real growth with FX effects.",
        status=status,
    )


def test_status_is_official_and_synthetic():
    assert DataStatus.OFFICIAL.is_official is True
    assert DataStatus.SYNTHETIC.is_official is False


def test_badge_labels_differ():
    assert "LIVE" in DataStatus.OFFICIAL.badge_label.upper()
    assert "SYNTHETIC" in DataStatus.SYNTHETIC.badge_label.upper()


def test_caption_includes_required_fields():
    meta = with_date_coverage(_sample_meta(), "2000-01-01", "2023-01-01")
    caption = meta.caption()
    assert "World Bank" in caption
    assert "current US$" in caption
    assert "annual" in caption
    assert "2000-01-01" in caption and "2023-01-01" in caption
    assert "LIVE / OFFICIAL" in caption


def test_caption_never_hides_synthetic_status():
    meta = _sample_meta(status=DataStatus.SYNTHETIC)
    caption = meta.caption()
    assert "SYNTHETIC" in caption
    assert "LIVE" not in caption or "SYNTHETIC / ILLUSTRATIVE" in caption


def test_with_status_appends_limitation_without_losing_original():
    meta = _sample_meta(status=DataStatus.OFFICIAL)
    updated = with_status(meta, DataStatus.SYNTHETIC, extra_limitation="Live fetch failed.")
    assert updated.status is DataStatus.SYNTHETIC
    assert "Live fetch failed." in updated.limitations
    assert "FX effects" in updated.limitations  # original limitation preserved
    # original object is untouched (frozen dataclass / immutability)
    assert meta.status is DataStatus.OFFICIAL


def test_transformations_always_a_tuple():
    meta = Metadata(
        indicator="x", source="s", provider="p", url="u", definition="d", unit="u2",
        frequency="annual", date_coverage="", transformations=["a", "b"], limitations="",
        status=DataStatus.OFFICIAL,
    )
    assert isinstance(meta.transformations, tuple)
    assert meta.transformations == ("a", "b")


def test_as_dict_round_trips_status_value():
    meta = _sample_meta(status=DataStatus.SYNTHETIC)
    d = meta.as_dict()
    assert d["status"] == "illustrative_synthetic"
    assert d["provider"] == "World Bank"
