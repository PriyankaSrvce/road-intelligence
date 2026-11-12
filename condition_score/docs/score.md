# Road Segment Condition Score

The score starts at 100. Each accepted damage detection subtracts a penalty
based on its severity, the fraction of the image covered by the damage, and
the detector's confidence. The penalties are added and divided by the number
of images surveyed on the segment:

```text
damage_load = sum(severity_weight * area_ratio * confidence) / n_images
score = clip(100 - SCORE_K * damage_load, 0, 100)
```

The configured severity weights are 1 for Low, 3 for Moderate, and 6 for High.
Detections with confidence below `MIN_CONFIDENCE` are ignored. Results are
clipped to the range 0-100.

## Worked example

Consider one High D40 detection with an `area_ratio` of `0.03` and confidence
`0.8`, on a segment with one surveyed image. The High weight is `6`, and
`SCORE_K` is `400`:

```text
damage_load = (6 * 0.03 * 0.8) / 1 = 0.144
score = 100 - 400 * 0.144 = 42.4
```

A score of `42.4` falls in the configured Poor band.
