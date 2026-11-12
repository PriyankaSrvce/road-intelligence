# Human Road Condition Ratings

Use the following guide to rate each surveyed road segment:

| Rating | Description |
|---:|---|
| 5 | Excellent |
| 4 | Minor wear |
| 3 | Moderate damage |
| 2 | Poor, needs repair soon |
| 1 | Very poor, unsafe |

**Rate the whole stretch you see, not the worst spot.**

## Create a rating sheet

Prepare a text file with one road segment ID per line, then run this command
from the project root:

```powershell
python scripts\make_rating_sheet.py --segments segments.txt --raters "Rater A,Rater B" --out ratings.csv
```

The generated CSV has one row per segment and rater, with blank `rating` and
`notes` fields to fill in.
