from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON, Boolean
from sqlalchemy.sql import func
from .database import Base
import enum


class RoleEnum(str, enum.Enum):
    user = "user"
    tailor = "tailor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # nullable for Google OAuth
    google_sub = Column(String, unique=True, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.user)
    credits = Column(Integer, default=100, nullable=False)  # AI credit balance
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OTPRecord(Base):
    """DB-backed OTP for email login. OTP is stored hashed."""
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_hash = Column(String, nullable=False)           # bcrypt / argon2 hash of the OTP
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImageType(str, enum.Enum):
    upload = "upload"
    generated = "generated"


class Image(Base):
    """Stores user-uploaded and AI-generated images."""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String, nullable=False)          # relative path: /uploads/<filename>
    image_type = Column(Enum(ImageType), default=ImageType.upload, nullable=False)
    prompt = Column(Text, nullable=True)                # non-null for generated images
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImageQuota(Base):
    """Tracks daily image upload quota per user."""
    __tablename__ = "image_quota"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)               # e.g. '2026-05-23'
    count = Column(Integer, default=0)


class StyleCritique(Base):
    """Stores AI style critiques (Ollama/qwen3.5:9b) per user. Response is markdown."""
    __tablename__ = "style_critiques"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)         # /uploads/<filename>
    markdown_response = Column(Text, nullable=False)    # Full markdown from Qwen
    credits_used = Column(Integer, nullable=False, default=5)
    model_used = Column(String, nullable=False, default="qwen3.5:9b")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CreditTransaction(Base):
    """Audit trail for all credit additions and deductions per user."""
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)            # negative = deduction, positive = top-up
    description = Column(String, nullable=False)        # e.g. "Style Critique analysis"
    service = Column(String, nullable=False)            # e.g. "genai", "auth"
    balance_after = Column(Integer, nullable=False)     # snapshot of balance after transaction
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    service = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FabricSimulation(Base):
    """Stores AI fabric simulations per user."""
    __tablename__ = "fabric_simulations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fabric_type = Column(String, nullable=False)        # e.g. "Silk", "Velvet"
    color = Column(String, nullable=False)              # e.g. "#d8c7b5"
    weight = Column(Integer, nullable=False)
    stiffness = Column(Integer, nullable=False)
    render_base64 = Column(Text, nullable=False)        # Base64 simulated output image
    credits_used = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

