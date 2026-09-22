from __future__ import annotations

import pandas as pd


def apply_filters(
    frame: pd.DataFrame,
    *,
    include_parts: bool,
    departments: list[str] | None,
    types: list[str] | None,
    licenses: list[str] | None,
    max_composite: int | None,
    gap_image: bool,
    gap_date_century: bool,
    gap_medium: bool,
    gap_attribution: bool,
    gap_description: bool,
) -> pd.DataFrame:
    if frame.empty:
        return frame

    df = frame.copy()
    if not include_parts:
        df = df[df["record_type"].isin(["object", "cover"])]

    if departments:
        df = df[df["department"].isin(departments)]
    if types:
        df = df[df["type"].isin(types)]
    if licenses:
        df = df[df["share_license_status"].isin(licenses)]
    if max_composite is not None:
        df = df[df["composite"] <= max_composite]
    if gap_image:
        df = df[df["has_gap_image"]]
    if gap_date_century:
        df = df[df["has_gap_date_century_or_worse"]]
    if gap_medium:
        df = df[df["has_gap_medium"]]
    if gap_attribution:
        df = df[df["has_gap_attribution"]]
    if gap_description:
        df = df[df["has_gap_description"]]

    return df.reset_index(drop=True)
