from prometheus_client import Counter, Gauge

# Custom Prometheus Metrics for Gym Portal
GYM_BOOKINGS_TOTAL = Counter(
    "gym_bookings_total",
    "Total number of bookings created",
    ["status"]
)

GYM_LATE_CANCELLATIONS_TOTAL = Counter(
    "gym_late_cancellations_total",
    "Total number of late cancellations that incurred penalties"
)

GYM_ACTIVE_STREAKS_TOTAL = Gauge(
    "gym_active_streaks_total",
    "Total cumulative active streaks across all members"
)

GYM_RESTRICTED_MEMBERS_TOTAL = Gauge(
    "gym_restricted_members_total",
    "Current total number of restricted gym members",
    ["status"]
)
