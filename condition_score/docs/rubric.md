# Road Damage Severity Rubric

The following thresholds classify a detection's `area_ratio` by damage code:

| Damage code | Low when area_ratio < | Moderate when area_ratio < | High when area_ratio >= |
|---|---:|---:|---:|
| D00 | 0.010 | 0.030 | 0.030 |
| D10 | 0.010 | 0.030 | 0.030 |
| D20 | 0.010 | 0.040 | 0.040 |
| D40 | 0.005 | 0.020 | 0.020 |

The lower threshold belongs to Moderate, and the upper threshold belongs to
High. Confidence below `0.30` causes the detection to be ignored and its
severity to be `None`; confidence equal to `0.30` is included.

`area_ratio` is the fraction of the image area covered by the detected damage,
expressed from `0` to `1`.

**These are draft values to be tuned on pilot data.**
