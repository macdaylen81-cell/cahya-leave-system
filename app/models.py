from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base
import enum
import datetime


class RoleEnum(str, enum.Enum):
    admin = "admin"      
    manager = "manager"
    hr = "hr"
    employee = "employee"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)   
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.employee, nullable=False)
    totp_secret = Column(String, nullable=True)
    is_totp_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Annual Leave Settings
    annual_leave_quota = Column(Integer, default=20)
    used_annual_leave = Column(Integer, default=0)
    replacement_leave_balance = Column(Integer, default=0)

    # Advanced Leave Policy Fields
    leave_year = Column(Integer, default=datetime.date.today().year)
    first_half_used = Column(Integer, default=0)
    second_half_used = Column(Integer, default=0)
    carry_forward_days = Column(Integer, default=0)
    carry_forward_expiry = Column(Date, nullable=True)
    must_change_password = Column(Boolean, default=False)

    leaves = relationship("LeaveRequest", back_populates="user")


class LeaveStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LeaveTypeEnum(str, enum.Enum):
    annual = "annual"
    replacement = "replacement"
    sick = "sick"
    emergency = "emergency"
    maternity = "maternity"
    unpaid = "unpaid"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(Enum(LeaveStatusEnum), default=LeaveStatusEnum.pending)
    leave_type = Column(Enum(LeaveTypeEnum), default=LeaveTypeEnum.annual, nullable=False)

    user = relationship("User", back_populates="leaves")


class OvertimeStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OvertimeRequest(Base):
    __tablename__ = "overtime_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    hours = Column(Integer, nullable=False)           
    approved_hours = Column(Float, nullable=True)     
    reason = Column(String, nullable=True)
    status = Column(Enum(OvertimeStatusEnum), default=OvertimeStatusEnum.pending)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    message = Column(String(500), nullable=False)
    link = Column(String(200), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User")


# ==================== PUBLIC HOLIDAY MODEL ====================
class PublicHoliday(Base):
    __tablename__ = "public_holidays"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    is_federal = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)