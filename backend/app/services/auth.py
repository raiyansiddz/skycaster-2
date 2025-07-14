import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User, UserRole
from app.models.subscription import Subscription, SubscriptionPlan
from app.schemas.auth import LoginRequest, RegisterRequest
from app.core.config import settings

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify a JWT token and return its payload"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    @staticmethod
    def register_user(db: Session, user_data: RegisterRequest) -> User:
        """Register a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        user = User(
            email=user_data.email,
            hashed_password=AuthService.hash_password(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            company=user_data.company,
            is_active=True,
            is_verified=False,  # Email verification required
            role=UserRole.USER
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default subscription (free tier)
        subscription = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.FREE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        db.add(subscription)
        db.commit()
        
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create_admin_user(db: Session) -> User:
        """Create admin user if not exists"""
        admin_user = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if admin_user:
            return admin_user
        
        admin_user = User(
            email=settings.ADMIN_EMAIL,
            hashed_password=AuthService.hash_password(settings.ADMIN_PASSWORD),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True,
            role=UserRole.ADMIN
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        return admin_user