import sys
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from condition.ratings import (
    make_rating_template,
    read_segment_ids,
    validate_ratings,
)


def test_template_normalizes_before_duplicate_check_and_lists_duplicate():
    with pytest.raises(ValueError, match="S1"):
        make_rating_template(["S1,", "S1"], ["A"])


def test_template_skips_blank_segment_and_rater_entries():
    template = make_rating_template(
        [" S1, ", "", "  ", "S2"], [" Asha, ", "", " Ravi "]
    )

    assert template["road_segment_id"].drop_duplicates().tolist() == ["S1", "S2"]
    assert template["rater"].drop_duplicates().tolist() == ["Asha", "Ravi"]
    assert len(template) == 4


def test_validate_ratings_reports_missing_pairs_separately():
    ratings = pd.DataFrame(
        {
            "road_segment_id": ["S1", "S2"],
            "rater": ["Asha", "Ravi"],
            "rating": [None, "  "],
        }
    )

    with pytest.raises(
        ValueError, match=r"Missing ratings for: S1/Asha, S2/Ravi"
    ):
        validate_ratings(ratings)


def test_validate_ratings_uses_bad_values_message_for_nonblank_invalid_rating():
    ratings = pd.DataFrame(
        {"road_segment_id": ["S1"], "rater": ["Asha"], "rating": [3.5]}
    )

    with pytest.raises(
        ValueError, match=r"Ratings must be whole numbers from 1 to 5"
    ):
        validate_ratings(ratings)


def test_read_segment_ids_ignores_blank_lines_and_trailing_commas(tmp_path):
    segments_file = tmp_path / "segments.txt"
    segments_file.write_text(" S1, \n\n   \nS2\n", encoding="utf-8")

    assert read_segment_ids(segments_file) == ["S1", "S2"]


def test_make_rating_sheet_script_writes_clean_rows(tmp_path):
    segments_file = tmp_path / "segments.txt"
    output_file = tmp_path / "ratings.csv"
    segments_file.write_text(" S1, \n\n   \nS2,\n", encoding="utf-8")
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "make_rating_sheet.py"

    subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--segments",
            str(segments_file),
            "--raters",
            "Asha,Ravi",
            "--out",
            str(output_file),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    result = pd.read_csv(output_file)

    assert result[["road_segment_id", "rater"]].values.tolist() == [
        ["S1", "Asha"],
        ["S1", "Ravi"],
        ["S2", "Asha"],
        ["S2", "Ravi"],
    ]
