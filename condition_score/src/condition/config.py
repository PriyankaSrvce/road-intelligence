# TO BE REPLACED by team shared-decisions file
CLASS_IDS = {}
SEVERITY_LEVELS = ["Low", "Moderate", "High"]
SCORE_BANDS = [
    ("Good", 80, 100),
    ("Fair", 60, 80),
    ("Poor", 40, 60),
    ("Very Poor", 0, 40),
]
DETECTION_COLUMNS = [
    "image_id",
    "road_segment_id",
    "class_id",
    "confidence",
    "x_min",
    "y_min",
    "x_max",
    "y_max",
    "area_ratio",
]

# DRAFT values, to be tuned on pilot data
MIN_CONFIDENCE = 0.30
SEVERITY_RUBRIC = {
    "D00": (0.010, 0.030),
    "D10": (0.010, 0.030),
    "D20": (0.010, 0.040),
    "D40": (0.005, 0.020),
}

# DRAFT values, to be tuned on pilot data
SEVERITY_WEIGHTS = {"Low": 1.0, "Moderate": 3.0, "High": 6.0}
SCORE_K = 400.0

RATING_MIN = 1
RATING_MAX = 5

# DRAFT values, to be tuned on pilot data
WEATHER_COLUMNS = ["rainfall_mm", "temp_c"]
RANDOM_SEED = 42
