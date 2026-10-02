"""initial postgis schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-21 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS Extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=15), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='farmer', nullable=False),
        sa.Column('language', sa.String(length=5), server_default='en', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )
    op.create_index('idx_users_phone', 'users', ['phone'], unique=True)

    # 3. Farmer Profiles Table
    op.create_table(
        'farmer_profiles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('village', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('total_area_acres', sa.Float(), server_default='0.0', nullable=False),
        sa.CheckConstraint('total_area_acres >= 0', name='chk_farmer_total_area_acres_non_negative'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('idx_farmer_profiles_district', 'farmer_profiles', ['district'])
    op.create_index('idx_farmer_profiles_location_gist', 'farmer_profiles', ['location'], postgresql_using='gist')

    # 4. Providers Table
    op.create_table(
        'providers',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('org_type', sa.String(length=20), server_default='owner', nullable=False),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # 5. Crops Table
    op.create_table(
        'crops',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('name_hi', sa.String(length=100), nullable=True),
        sa.Column('name_mr', sa.String(length=100), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_crops_name', 'crops', ['name'], unique=True)

    # 6. Crop Stages Table
    op.create_table(
        'crop_stages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('stage_name', sa.String(length=100), nullable=False),
        sa.Column('start_day', sa.Integer(), nullable=False),
        sa.Column('end_day', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crop_stages_crop_id', 'crop_stages', ['crop_id'])

    # 7. Nutrient Rules Table
    op.create_table(
        'nutrient_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('stage_id', sa.Integer(), nullable=True),
        sa.Column('nutrient', sa.String(length=50), nullable=False),
        sa.Column('condition_json', sa.JSON(), nullable=False),
        sa.Column('guidance_text', sa.Text(), nullable=False),
        sa.Column('input_category', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=255), server_default='SAMPLE - verify with ICAR / state agriculture dept', nullable=False),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['crop_stages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_nutrient_rules_crop_id', 'nutrient_rules', ['crop_id'])

    # 8. Farms Table
    op.create_table(
        'farms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('sowing_date', sa.Date(), nullable=False),
        sa.Column('area_acres', sa.Float(), nullable=False),
        sa.Column('soil_type', sa.String(length=50), nullable=True),
        sa.Column('current_stage', sa.String(length=100), nullable=True),
        sa.Column('irrigation_type', sa.String(length=50), nullable=True),
        sa.CheckConstraint('area_acres > 0', name='chk_farm_area_acres_positive'),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_farms_farmer_id', 'farms', ['farmer_id'])
    op.create_index('idx_farms_crop_id', 'farms', ['crop_id'])

    # 9. Soil Tests Table
    op.create_table(
        'soil_tests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('ph', sa.Float(), nullable=False),
        sa.Column('nitrogen', sa.Float(), nullable=True),
        sa.Column('phosphorus', sa.Float(), nullable=True),
        sa.Column('potassium', sa.Float(), nullable=True),
        sa.Column('organic_carbon', sa.Float(), nullable=True),
        sa.Column('tested_on', sa.Date(), nullable=False),
        sa.CheckConstraint('ph >= 0 AND ph <= 14', name='chk_soil_ph_valid_range'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_soil_tests_farm_id', 'soil_tests', ['farm_id'])

    # 10. Fertilizer History Table
    op.create_table(
        'fertilizer_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('product_category', sa.String(length=100), nullable=False),
        sa.Column('applied_on', sa.Date(), nullable=False),
        sa.Column('quantity_kg', sa.Float(), nullable=False),
        sa.CheckConstraint('quantity_kg > 0', name='chk_fertilizer_quantity_positive'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_fertilizer_history_farm_id', 'fertilizer_history', ['farm_id'])

    # 11. Machine Types Table
    op.create_table(
        'machine_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('name_hi', sa.String(length=100), nullable=True),
        sa.Column('name_mr', sa.String(length=100), nullable=True),
        sa.Column('typical_rate_per_acre', sa.Float(), nullable=False),
        sa.Column('mobilization_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_machine_types_name', 'machine_types', ['name'], unique=True)

    # 12. Machines Table
    op.create_table(
        'machines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('machine_type_id', sa.Integer(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('rate_per_acre', sa.Float(), nullable=False),
        sa.Column('available_from', sa.Date(), nullable=False),
        sa.Column('available_to', sa.Date(), nullable=False),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('rating', sa.Float(), server_default='4.5', nullable=False),
        sa.CheckConstraint('rate_per_acre > 0', name='chk_machine_rate_positive'),
        sa.CheckConstraint('rating >= 0 AND rating <= 5', name='chk_machine_rating_range'),
        sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_machines_provider_id', 'machines', ['provider_id'])
    op.create_index('idx_machines_machine_type_id', 'machines', ['machine_type_id'])
    op.create_index('idx_machines_location_gist', 'machines', ['location'], postgresql_using='gist')

    # 13. Crop Machine Map Table
    op.create_table(
        'crop_machine_map',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('stage_id', sa.Integer(), nullable=True),
        sa.Column('machine_type_id', sa.Integer(), nullable=False),
        sa.Column('days_offset', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['crop_stages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crop_machine_map_crop_id', 'crop_machine_map', ['crop_id'])

    # 14. Booking Groups Table
    op.create_table(
        'booking_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('machine_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('min_farmers', sa.Integer(), server_default='2', nullable=False),
        sa.Column('max_acres', sa.Float(), server_default='20.0', nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.CheckConstraint('min_farmers > 0', name='chk_group_min_farmers_positive'),
        sa.CheckConstraint('max_acres > 0', name='chk_group_max_acres_positive'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_booking_groups_machine_id', 'booking_groups', ['machine_id'])

    # 15. Group Members Table (with UNIQUE constraint on group_id, farmer_id)
    op.create_table(
        'group_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('acres', sa.Float(), nullable=False),
        sa.Column('share_amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='joined', nullable=False),
        sa.CheckConstraint('acres > 0', name='chk_group_member_acres_positive'),
        sa.CheckConstraint('share_amount >= 0', name='chk_group_member_share_non_negative'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['booking_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'farmer_id', name='uq_group_members_group_farmer')
    )
    op.create_index('idx_group_members_group_id', 'group_members', ['group_id'])
    op.create_index('idx_group_members_farmer_id', 'group_members', ['farmer_id'])

    # 16. Input Sellers Table
    op.create_table(
        'input_sellers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('categories', sa.ARRAY(sa.String(length=50)), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_input_sellers_location_gist', 'input_sellers', ['location'], postgresql_using='gist')

    # 17. Notifications Table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel', sa.String(length=20), server_default='in_app', nullable=False),
        sa.Column('read', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('input_sellers')
    op.drop_table('group_members')
    op.drop_table('booking_groups')
    op.drop_table('crop_machine_map')
    op.drop_table('machines')
    op.drop_table('machine_types')
    op.drop_table('fertilizer_history')
    op.drop_table('soil_tests')
    op.drop_table('farms')
    op.drop_table('nutrient_rules')
    op.drop_table('crop_stages')
    op.drop_table('crops')
    op.drop_table('providers')
    op.drop_table('farmer_profiles')
    op.drop_table('users')
