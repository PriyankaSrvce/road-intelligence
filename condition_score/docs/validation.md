# Score Validation

Validation compares how consistently people rate the same road segments and
whether those ratings move together with the automatic condition score.

- **Cohen's kappa** is used for two raters. It measures agreement while
  accounting for agreement that could happen by chance; quadratic weighting
  gives partial credit to ratings that are close.
- **ICC (intraclass correlation)** is used for three or more raters. It
  measures how consistently raters distinguish segments. The analysis reports
  ICC2k and ICC3k for the average ratings.
- **Spearman correlation** compares score and mean rating ranks. It indicates
  whether segments scored as better also tend to receive better human ratings.

Agreement values below 0.40 are poor, 0.40 to below 0.60 are fair, 0.60 to
below 0.75 are good, and 0.75 or higher are excellent.

**Freeze rule:** once a score version has been validated, tag that score
version and do not change its weights. Any weight changes should be treated as
a new score version and validated again.
