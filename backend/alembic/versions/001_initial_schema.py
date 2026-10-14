"""Initial migration for Gym Portal models

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-14 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. members
    op.create_table(
        'members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('membership_type', sa.Enum('BASIC', 'PREMIUM', name='membershiptype'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('penalty_points', sa.Integer(), server_default='0', nullable=False),
        sa.Column('restriction_status', sa.Enum('NONE', 'SAME_DAY_ONLY', 'FROZEN', name='restrictionstatus'), server_default='NONE', nullable=False),
        sa.Column('restriction_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_members_email'), 'members', ['email'], unique=True)
    op.create_index(op.f('ix_members_id'), 'members', ['id'], unique=False)

    # 2. streak_profiles
    op.create_table(
        'streak_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('weekly_target_days', sa.Integer(), server_default='3', nullable=False),
        sa.Column('current_streak_weeks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('attended_this_week', sa.Integer(), server_default='0', nullable=False),
        sa.Column('lives_remaining', sa.Integer(), server_default='3', nullable=False),
        sa.Column('lives_earned_this_week', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_week_processed', sa.Date(), nullable=True),
        sa.CheckConstraint('weekly_target_days >= 1 AND weekly_target_days <= 7', name='check_weekly_target_range'),
        sa.CheckConstraint('lives_remaining >= 0 AND lives_remaining <= 3', name='check_lives_remaining_range'),
        sa.CheckConstraint('lives_earned_this_week >= 0 AND lives_earned_this_week <= 1', name='check_lives_earned_range'),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('member_id')
    )
    op.create_index(op.f('ix_streak_profiles_id'), 'streak_profiles', ['id'], unique=False)

    # 3. achievements
    op.create_table(
        'achievements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('achievement_type', sa.Enum('OVER_ACHIEVER_1_WEEK', 'OVER_ACHIEVER_2_WEEKS', 'STREAK_MILESTONE_4_WEEKS', 'ATTENDED_5_PLUS_CLASSES', name='achievementtype'), nullable=False),
        sa.Column('lives_awarded', sa.Integer(), server_default='1', nullable=False),
        sa.Column('earned_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_achievements_id'), 'achievements', ['id'], unique=False)

    # 4. slots
    op.create_table(
        'slots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.CheckConstraint('capacity > 0', name='check_slot_capacity_positive'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slots_id'), 'slots', ['id'], unique=False)
    op.create_index(op.f('ix_slots_start_time'), 'slots', ['start_time'], unique=False)

    # 5. bookings
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('slot_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW', name='bookingstatus'), server_default='CONFIRMED', nullable=False),
        sa.Column('penalty_applied', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['slot_id'], ['slots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)

    # 6. support_tickets
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'RESOLVED', 'REJECTED', name='ticketstatus'), server_default='OPEN', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_tickets_id'), 'support_tickets', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('support_tickets')
    op.drop_table('bookings')
    op.drop_table('slots')
    op.drop_table('achievements')
    op.drop_table('streak_profiles')
    op.drop_table('members')
