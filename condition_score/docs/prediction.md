# Temporal Prediction

The temporal table keeps each road segment's score at each survey date and
adds weather information for that date. `days_since_prev` records the gap
from the previous survey, `prev_score` is the prior score, and `prev_rate` is
the deterioration rate available from the preceding interval.
`deterioration_rate` is `(prev_score - score) / days_since_prev`; a positive
value means the condition is getting worse. `next_score` is the following
survey's score and is the prediction target.

The persistence baseline predicts that the next score will equal today's
score. The linear-trend baseline extends the most recently available
deterioration rate across the average survey interval. Random forest and
XGBoost models use current and prior scores, trend features, elapsed days, and
weather.

Evaluation uses **time-based splits**: earlier surveys train the models and
later surveys test them. Random splits could let information from later dates
leak into training, making future predictions look better than they are.

Report all model results honestly. If tree models do not beat the baselines,
say so; do not imply that added complexity improved prediction.
