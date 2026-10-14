from datetime import datetime, timezone, timedelta
from freezegun import freeze_time
from app.models.models import (
    Member,
    Slot,
    Booking,
    StreakProfile,
    SupportTicket,
    RestrictionStatus,
    BookingStatus,
)
from app.services.streak_service import evaluate_member_week
from app.services.analytics_service import reset_monthly_penalty_points
from app.services.cancellation_service import record_no_show


def test_01_health_and_ready_endpoints(client):
    """Verifies /health returns 200 OK and /ready verifies DB connection."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


def test_02_create_booking_success(client, db_session):
    """Validates successful booking creation when capacity is available."""
    now = datetime.now(timezone.utc)
    member = Member(name="Alice", email="alice@test.com", is_active=True)
    slot = Slot(title="Morning HIIT", capacity=5, start_time=now + timedelta(hours=4), end_time=now + timedelta(hours=5))
    db_session.add_all([member, slot])
    db_session.commit()

    res = client.post("/api/v1/bookings", json={"member_id": member.id, "slot_id": slot.id})
    assert res.status_code == 201
    data = res.json()
    assert data["member_id"] == member.id
    assert data["slot_id"] == slot.id
    assert data["status"] == "CONFIRMED"


def test_03_booking_exceeds_capacity_failure(client, db_session):
    """Asserts 400 Bad Request when booking a full slot."""
    now = datetime.now(timezone.utc)
    member1 = Member(name="Alice", email="alice@test.com", is_active=True)
    member2 = Member(name="Bob", email="bob@test.com", is_active=True)
    slot = Slot(title="Pilates", capacity=1, start_time=now + timedelta(hours=5), end_time=now + timedelta(hours=6))
    db_session.add_all([member1, member2, slot])
    db_session.commit()

    # Member 1 books slot (occupies 1/1)
    res1 = client.post("/api/v1/bookings", json={"member_id": member1.id, "slot_id": slot.id})
    assert res1.status_code == 201

    # Member 2 attempts booking
    res2 = client.post("/api/v1/bookings", json={"member_id": member2.id, "slot_id": slot.id})
    assert res2.status_code == 400
    assert "Slot fully booked" in res2.json()["detail"]


def test_04_duplicate_booking_failure(client, db_session):
    """Asserts 409 Conflict when a member books the same slot twice."""
    now = datetime.now(timezone.utc)
    member = Member(name="Charlie", email="charlie@test.com", is_active=True)
    slot = Slot(title="Zumba", capacity=10, start_time=now + timedelta(hours=5), end_time=now + timedelta(hours=6))
    db_session.add_all([member, slot])
    db_session.commit()

    res1 = client.post("/api/v1/bookings", json={"member_id": member.id, "slot_id": slot.id})
    assert res1.status_code == 201

    res2 = client.post("/api/v1/bookings", json={"member_id": member.id, "slot_id": slot.id})
    assert res2.status_code == 409
    assert "already booked" in res2.json()["detail"]


def test_05_inactive_member_booking_failure(client, db_session):
    """Asserts 403 Forbidden when is_active == False."""
    now = datetime.now(timezone.utc)
    member = Member(name="Suspended Member", email="inactive@test.com", is_active=False)
    slot = Slot(title="Yoga", capacity=10, start_time=now + timedelta(hours=5), end_time=now + timedelta(hours=6))
    db_session.add_all([member, slot])
    db_session.commit()

    res = client.post("/api/v1/bookings", json={"member_id": member.id, "slot_id": slot.id})
    assert res.status_code == 403
    assert "inactive" in res.json()["detail"]


def test_06_cancellation_grace_period_success(client, db_session):
    """Cancelling >= 2 hours before class applies 0 penalty points."""
    with freeze_time("2026-10-14 10:00:00"):
        slot_time = datetime(2026, 10, 14, 13, 0, 0, tzinfo=timezone.utc) # 3 hours away
        member = Member(name="Grace", email="grace@test.com", penalty_points=0)
        slot = Slot(title="Spin", capacity=5, start_time=slot_time, end_time=slot_time + timedelta(hours=1))
        db_session.add_all([member, slot])
        db_session.commit()

        booking = Booking(member_id=member.id, slot_id=slot.id, status=BookingStatus.CONFIRMED)
        db_session.add(booking)
        db_session.commit()

        res = client.delete(f"/api/v1/bookings/{booking.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["penalty_applied"] is False
        assert data["penalty_points"] == 0


def test_07_late_cancellation_applies_penalty_point(client, db_session):
    """Cancelling < 2 hours before class applies +1 penalty point."""
    with freeze_time("2026-10-14 10:00:00"):
        slot_time = datetime(2026, 10, 14, 11, 30, 0, tzinfo=timezone.utc) # 1.5 hours away
        member = Member(name="Late Member", email="late@test.com", penalty_points=0)
        slot = Slot(title="Cardio", capacity=5, start_time=slot_time, end_time=slot_time + timedelta(hours=1))
        db_session.add_all([member, slot])
        db_session.commit()

        booking = Booking(member_id=member.id, slot_id=slot.id, status=BookingStatus.CONFIRMED)
        db_session.add(booking)
        db_session.commit()

        res = client.delete(f"/api/v1/bookings/{booking.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["penalty_applied"] is True
        assert data["penalty_points"] == 1
        assert "Late cancellation penalty applied" in data["warning"]


def test_08_no_show_applies_penalty_point(client, db_session):
    """Marking booking as NO_SHOW applies +1 penalty point."""
    now = datetime.now(timezone.utc)
    member = Member(name="NoShow Member", email="noshow@test.com", penalty_points=0)
    slot = Slot(title="Crossfit", capacity=5, start_time=now, end_time=now + timedelta(hours=1))
    db_session.add_all([member, slot])
    db_session.commit()

    booking = Booking(member_id=member.id, slot_id=slot.id, status=BookingStatus.CONFIRMED)
    db_session.add(booking)
    db_session.commit()

    record_no_show(db_session, booking.id)
    db_session.refresh(member)
    db_session.refresh(booking)

    assert booking.status == BookingStatus.NO_SHOW
    assert booking.penalty_applied is True
    assert member.penalty_points == 1


def test_09_penalty_tier2_same_day_ban_trigger(client, db_session):
    """Accumulating 3 penalty points sets SAME_DAY_ONLY ban for 7 days."""
    with freeze_time("2026-10-14 10:00:00"):
        now = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)
        member = Member(name="Tier2 Member", email="tier2@test.com", penalty_points=2)
        slot = Slot(title="Bootcamp", capacity=5, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
        db_session.add_all([member, slot])
        db_session.commit()

        booking = Booking(member_id=member.id, slot_id=slot.id, status=BookingStatus.CONFIRMED)
        db_session.add(booking)
        db_session.commit()

        # Cancelling late causes points to go 2 -> 3
        res = client.delete(f"/api/v1/bookings/{booking.id}")
        assert res.status_code == 200
        db_session.refresh(member)
        assert member.penalty_points == 3
        assert member.restriction_status == RestrictionStatus.SAME_DAY_ONLY
        assert member.restriction_until.replace(tzinfo=timezone.utc) == now + timedelta(days=7)


def test_10_same_day_ban_rejects_advance_booking(client, db_session):
    """Asserts 403 Forbidden for advance bookings (> 2 hrs) under SAME_DAY_ONLY ban."""
    with freeze_time("2026-10-14 10:00:00"):
        now = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)
        member = Member(
            name="Restricted Member",
            email="restricted@test.com",
            penalty_points=3,
            restriction_status=RestrictionStatus.SAME_DAY_ONLY,
            restriction_until=now + timedelta(days=5),
        )
        # Advance slot (4 hours away)
        slot = Slot(title="Evening Yoga", capacity=5, start_time=now + timedelta(hours=4), end_time=now + timedelta(hours=5))
        db_session.add_all([member, slot])
        db_session.commit()

        res = client.post("/api/v1/bookings", json={"member_id": member.id, "slot_id": slot.id})
        assert res.status_code == 403
        assert "Same-day restriction active" in res.json()["detail"]


def test_11_same_day_ban_allows_short_notice_booking(client, db_session):
    """Permits bookings starting in <= 2 hrs under SAME_DAY_ONLY ban."""
    with freeze_time("2026-10-14 10:00:00"):
        now = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)
        member = Member(
            name="Restricted Member",
            email="restr_short@test.com",
            penalty_points=3,
            restriction_status=RestrictionStatus.SAME_DAY_ONLY,
            restriction_until=now + timedelta(days=5),
        )
        # Short notice slot (1.5 hours away <= 2 hours)
        slot = Slot(title="Immediate Gym", capacity=5, start_time=now + timedelta(minutes=90), end_time=now + timedelta(minutes=150))
        db_session.add_all([member, slot])
        db_session.commit()

        res = client.post("/api/v1/bookings", json={"member_id": member.id, "slot_id": slot.id})
        assert res.status_code == 201
        assert res.json()["status"] == "CONFIRMED"


def test_12_repeated_offense_extends_ban_and_freezes_account(client, db_session):
    """Validates 14-day ban extension and FROZEN escalation."""
    with freeze_time("2026-10-14 10:00:00"):
        now = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone.utc)
        # Member already under Tier 2 ban
        member = Member(
            name="Repeat Offender",
            email="repeat@test.com",
            penalty_points=3,
            restriction_status=RestrictionStatus.SAME_DAY_ONLY,
            restriction_until=now + timedelta(days=5),
        )
        slot1 = Slot(title="Slot 1", capacity=5, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
        slot2 = Slot(title="Slot 2", capacity=5, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
        db_session.add_all([member, slot1, slot2])
        db_session.commit()

        # 4th offense (while restricted) -> Tier 3: extends to NOW + 14 days
        b1 = Booking(member_id=member.id, slot_id=slot1.id, status=BookingStatus.CONFIRMED)
        db_session.add(b1)
        db_session.commit()
        client.delete(f"/api/v1/bookings/{b1.id}")
        db_session.refresh(member)
        assert member.penalty_points == 4
        assert member.restriction_until.replace(tzinfo=timezone.utc) == now + timedelta(days=14)

        # 5th offense (further offense) -> Tier 4: FROZEN for 7 days
        b2 = Booking(member_id=member.id, slot_id=slot2.id, status=BookingStatus.CONFIRMED)
        db_session.add(b2)
        db_session.commit()
        client.delete(f"/api/v1/bookings/{b2.id}")
        db_session.refresh(member)
        assert member.penalty_points == 5
        assert member.restriction_status == RestrictionStatus.FROZEN
        assert member.restriction_until.replace(tzinfo=timezone.utc) == now + timedelta(days=7)


def test_13_customer_support_ticket_clears_penalty_and_ban(client, db_session):
    """Resolving a support ticket resets points to 0 and clears bans."""
    now = datetime.now(timezone.utc)
    member = Member(
        name="Dispute Member",
        email="dispute@test.com",
        penalty_points=5,
        restriction_status=RestrictionStatus.FROZEN,
        restriction_until=now + timedelta(days=7),
    )
    db_session.add(member)
    db_session.commit()

    ticket = SupportTicket(member_id=member.id, reason="Emergency room visit with medical note")
    db_session.add(ticket)
    db_session.commit()

    res = client.post(f"/api/v1/support/tickets/{ticket.id}/resolve", json={"action": "APPROVE"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESOLVED"
    assert data["penalty_points"] == 0
    assert data["restriction_status"] == "NONE"

    db_session.refresh(member)
    assert member.penalty_points == 0
    assert member.restriction_status == RestrictionStatus.NONE
    assert member.restriction_until is None


def test_14_weekly_target_achieved_increments_streak(client, db_session):
    """Completing >= N classes increments streak by +1."""
    member = Member(name="Dedicated Runner", email="runner@test.com")
    db_session.add(member)
    db_session.commit()

    profile = StreakProfile(
        member_id=member.id,
        weekly_target_days=3,
        current_streak_weeks=2,
        attended_this_week=3, # Met target exactly
        lives_remaining=3,
    )
    db_session.add(profile)
    db_session.commit()

    evaluate_member_week(db_session, profile)
    db_session.refresh(profile)

    assert profile.current_streak_weeks == 3
    assert profile.attended_this_week == 0
    assert profile.lives_remaining == 3


def test_15_streak_deficit_consumes_life_and_protects_streak(client, db_session):
    """Completing < N classes deducts 1 life without losing streak."""
    member = Member(name="Busy Member", email="busy@test.com")
    db_session.add(member)
    db_session.commit()

    profile = StreakProfile(
        member_id=member.id,
        weekly_target_days=4,
        current_streak_weeks=5,
        attended_this_week=2, # Target not met (2 < 4)
        lives_remaining=3,
    )
    db_session.add(profile)
    db_session.commit()

    evaluate_member_week(db_session, profile)
    db_session.refresh(profile)

    # Life consumed, streak preserved
    assert profile.lives_remaining == 2
    assert profile.current_streak_weeks == 5
    assert profile.attended_this_week == 0


def test_16_exhausted_lives_resets_streak_to_zero(client, db_session):
    """Completing < N classes with 0 lives resets streak to 0."""
    member = Member(name="Streak Break", email="broken@test.com")
    db_session.add(member)
    db_session.commit()

    profile = StreakProfile(
        member_id=member.id,
        weekly_target_days=3,
        current_streak_weeks=4,
        attended_this_week=1, # Target missed
        lives_remaining=0, # No lives left to consume
    )
    db_session.add(profile)
    db_session.commit()

    evaluate_member_week(db_session, profile)
    db_session.refresh(profile)

    assert profile.current_streak_weeks == 0
    assert profile.lives_remaining == 3 # Default 3 lives restored on reset


def test_17_achievement_awards_life_respects_max_cap_of_3(client, db_session):
    """Achievement awards life but caps lives_remaining at 3."""
    member = Member(name="Overachiever", email="over@test.com")
    db_session.add(member)
    db_session.commit()

    profile = StreakProfile(
        member_id=member.id,
        weekly_target_days=3,
        current_streak_weeks=1,
        attended_this_week=5, # Over-achiever
        lives_remaining=3, # Already at maximum cap 3
        lives_earned_this_week=0,
    )
    db_session.add(profile)
    db_session.commit()

    evaluate_member_week(db_session, profile)
    db_session.refresh(profile)

    assert profile.lives_remaining == 3 # Remains capped at 3


def test_18_weekly_earned_life_limit_enforced(client, db_session):
    """Asserts that achieving multiple achievements in the same week awards ONLY 1 extra life max."""
    member = Member(name="Multi Achiever", email="multi@test.com")
    db_session.add(member)
    db_session.commit()

    profile = StreakProfile(
        member_id=member.id,
        weekly_target_days=2,
        current_streak_weeks=3, # Next week will reach 4-week milestone
        attended_this_week=5, # Triggers OVER_ACHIEVER_1_WEEK + ATTENDED_5_PLUS_CLASSES
        lives_remaining=1, # 1 life remaining, can absorb extra life
        lives_earned_this_week=0,
    )
    db_session.add(profile)
    db_session.commit()

    evaluate_member_week(db_session, profile)
    db_session.refresh(profile)

    # Must only gain exactly +1 life even though multiple criteria met
    assert profile.lives_remaining == 2
    assert profile.current_streak_weeks == 4


def test_19_monthly_cron_resets_penalty_points(client, db_session):
    """Monthly reset clears penalty points to 0."""
    now = datetime.now(timezone.utc)
    m1 = Member(name="M1", email="m1@test.com", penalty_points=4)
    m2 = Member(name="M2", email="m2@test.com", penalty_points=1)
    db_session.add_all([m1, m2])
    db_session.commit()

    reset_monthly_penalty_points(db_session)
    db_session.refresh(m1)
    db_session.refresh(m2)

    assert m1.penalty_points == 0
    assert m2.penalty_points == 0
