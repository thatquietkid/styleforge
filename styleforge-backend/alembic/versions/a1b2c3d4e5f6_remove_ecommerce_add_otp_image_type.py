"""Remove e-commerce tables; add otp_records; add image_type + prompt cols to images; update roleenum

Revision ID: a1b2c3d4e5f6
Revises: 52544c2c6bf8
Create Date: 2026-05-23 18:00:00.000000

Changes:
- Drop product_images, order_items, cart_items (leaf tables first)
- Drop orders, products, carts, categories (parent tables)
- Drop associated PG enums: orderstatus
- Update roleenum to remove 'seller'
- Add image_type column to images
- Add prompt column to images
- Create otp_records table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '52544c2c6bf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Drop e-commerce leaf tables (FK children first)
    # -----------------------------------------------------------------------
    op.drop_index('ix_product_images_id', table_name='product_images', if_exists=True)
    op.drop_table('product_images')

    op.drop_index('ix_order_items_id', table_name='order_items', if_exists=True)
    op.drop_table('order_items')

    op.drop_index('ix_cart_items_id', table_name='cart_items', if_exists=True)
    op.drop_table('cart_items')

    # -----------------------------------------------------------------------
    # 2. Drop e-commerce parent tables
    # -----------------------------------------------------------------------
    op.drop_index('ix_products_id', table_name='products', if_exists=True)
    op.drop_table('products')

    op.drop_index('ix_orders_id', table_name='orders', if_exists=True)
    op.drop_table('orders')

    op.drop_index('ix_carts_id', table_name='carts', if_exists=True)
    op.drop_table('carts')

    op.drop_index('ix_categories_id', table_name='categories', if_exists=True)
    op.drop_table('categories')

    # -----------------------------------------------------------------------
    # 3. Drop the orderstatus postgres enum
    # -----------------------------------------------------------------------
    op.execute("DROP TYPE IF EXISTS orderstatus")

    # -----------------------------------------------------------------------
    # 4. Update roleenum — remove 'seller', keep user/tailor/admin
    #    PostgreSQL enums cannot have values removed, so we:
    #    a) Update any 'seller' rows to 'user'
    #    b) Create a new enum type, alter the column, drop old type
    # -----------------------------------------------------------------------
    op.execute("UPDATE users SET role = 'user' WHERE role = 'seller'")
    op.execute("ALTER TYPE roleenum RENAME TO roleenum_old")
    op.execute("CREATE TYPE roleenum AS ENUM ('user', 'tailor', 'admin')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE roleenum USING role::text::roleenum")
    op.execute("DROP TYPE roleenum_old")

    # -----------------------------------------------------------------------
    # 5. Add image_type column to images table
    # -----------------------------------------------------------------------
    op.execute("CREATE TYPE imagetype AS ENUM ('upload', 'generated')")
    op.add_column(
        'images',
        sa.Column(
            'image_type',
            sa.Enum('upload', 'generated', name='imagetype'),
            nullable=False,
            server_default='upload',
        ),
    )
    # Remove the server default after backfill (keep stored values)
    op.alter_column('images', 'image_type', server_default=None)

    # -----------------------------------------------------------------------
    # 6. Add prompt column to images table (nullable — only for generated)
    # -----------------------------------------------------------------------
    op.add_column(
        'images',
        sa.Column('prompt', sa.Text(), nullable=True),
    )

    # -----------------------------------------------------------------------
    # 7. Create otp_records table
    # -----------------------------------------------------------------------
    op.create_table(
        'otp_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('otp_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_otp_records_id'), 'otp_records', ['id'], unique=False)
    op.create_index(op.f('ix_otp_records_email'), 'otp_records', ['email'], unique=False)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Reverse: drop otp_records
    # -----------------------------------------------------------------------
    op.drop_index('ix_otp_records_email', table_name='otp_records')
    op.drop_index('ix_otp_records_id', table_name='otp_records')
    op.drop_table('otp_records')

    # -----------------------------------------------------------------------
    # Remove new image columns
    # -----------------------------------------------------------------------
    op.drop_column('images', 'prompt')
    op.drop_column('images', 'image_type')
    op.execute("DROP TYPE IF EXISTS imagetype")

    # -----------------------------------------------------------------------
    # Restore roleenum with 'seller'
    # -----------------------------------------------------------------------
    op.execute("ALTER TYPE roleenum RENAME TO roleenum_old")
    op.execute("CREATE TYPE roleenum AS ENUM ('user', 'tailor', 'seller', 'admin')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE roleenum USING role::text::roleenum")
    op.execute("DROP TYPE roleenum_old")

    # -----------------------------------------------------------------------
    # Re-create e-commerce tables (schema only — data is gone)
    # -----------------------------------------------------------------------
    op.execute("CREATE TYPE orderstatus AS ENUM ('pending', 'paid', 'shipped', 'delivered', 'cancelled')")

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_categories_id', 'categories', ['id'], unique=False)

    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_products_id', 'products', ['id'], unique=False)

    op.create_table(
        'carts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_carts_id', 'carts', ['id'], unique=False)

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'paid', 'shipped', 'delivered', 'cancelled', name='orderstatus'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_orders_id', 'orders', ['id'], unique=False)

    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cart_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cart_items_id', 'cart_items', ['id'], unique=False)

    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_order_items_id', 'order_items', ['id'], unique=False)

    op.create_table(
        'product_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_product_images_id', 'product_images', ['id'], unique=False)
