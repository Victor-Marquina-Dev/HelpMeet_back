from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from helpmeet_licenses.database import Base


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    gumroad_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    licenses = relationship("License", back_populates="customer")


class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False)
    key_last4 = Column(String(4), nullable=False)
    plan = Column(String(50), default="personal")
    status = Column(String(30), default="active")
    updates_until = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    customer = relationship("Customer", back_populates="licenses")
    activations = relationship("Activation", back_populates="license")
    events = relationship("LicenseEvent", back_populates="license")


class Activation(Base):
    __tablename__ = "activations"
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)
    device_id_hash = Column(String(64), nullable=False)
    device_name = Column(String(255))
    os = Column(String(100))
    app_version = Column(String(30))
    status = Column(String(30), default="active")
    first_activated_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    deactivated_at = Column(DateTime)
    license = relationship("License", back_populates="activations")


class LicenseEvent(Base):
    __tablename__ = "license_events"
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_metadata = Column("metadata", JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    license = relationship("License", back_populates="events")
