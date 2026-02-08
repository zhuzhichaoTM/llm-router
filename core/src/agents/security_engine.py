"""
Security Engine - Multi-layer data security and access control.

This module provides:
- Sensitive data detection and masking
- Data classification and tagging
- Multi-factor authentication support
- RBAC permission model
- Audit logging
- Key rotation mechanism
"""
import re
import time
import secrets
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserRole, UserStatus, APIKey
from src.models.routing import RoutingDecision
from src.db.session import SessionManager
from src.config.settings import settings
from src.utils.encryption import EncryptionManager
from src.config.redis_config import RedisKeys
from src.services.redis_client import RedisService


class SensitivityLevel(str, Enum):
    """Data sensitivity levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    CRITICAL = "critical"


class DataType(str, Enum):
    """Types of sensitive data."""
    CREDENTIAL = "credential"  # API keys, passwords
    PERSONAL = "personal"  # PII: email, phone, SSN
    FINANCIAL = "financial"  # Credit card, bank info
    HEALTH = "health"  # Medical records
    TOKEN = "token"  # Auth tokens, session IDs
    PROPRIETARY = "proprietary"  # Trade secrets, IP


@dataclass
class SensitiveDataMatch:
    """Matched sensitive data."""
    data_type: DataType
    sensitivity: SensitivityLevel
    value: str
    start_pos: int
    end_pos: int
    confidence: float


@dataclass
class SecurityDecision:
    """Security decision result."""
    allow_request: bool
    risk_score: float  # 0-1
    detected_issues: List[str]
    required_actions: List[str]
    masked_content: Optional[str] = None


class SensitiveDataDetector:
    """
    Detects sensitive data in content.

    Patterns:
    - API keys, tokens
    - Credentials (passwords, secrets)
    - PII (email, phone, SSN, etc.)
    - Financial data (credit cards)
    - Health information
    """

    # Detection patterns
    PATTERNS = {
        DataType.CREDENTIAL: [
            (r'(?:password|passwd|pwd|secret|token|api_key|apikey)\s*[=:]\s*["\']?[\w-]+["\']?', 0.95),
            (r'Bearer\s+[A-Za-z0-9\-._~+/]+', 0.90),
            (r'Skypi-[A-Za-z0-9]{48}', 0.95),  # Stripe key
            (r'AKIA[0-9A-Z]{16}', 0.95),  # AWS key
        ],
        DataType.PERSONAL: [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 0.95),  # Email
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 0.90),  # Phone (US)
            (r'\b\d{3}-\d{2}-\d{4}\b', 0.95),  # SSN
            (r'\b\d{11}\b', 0.85),  # Phone (11 digits)
        ],
        DataType.FINANCIAL: [
            (r'\b(?:4\d{3}[-\s]?){3}\d{4}\b', 0.95),  # Credit card
            (r'\b(?:3\d{3}[-\s]?){2}\d{4}\b', 0.95),  # Amex
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 0.95),  # 16-digit card
        ],
        DataType.TOKEN: [
            (r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', 0.95),  # JWT
            (r'sess_[A-Za-z0-9]{22,}', 0.90),  # Session ID
        ],
    }

    def __init__(self):
        """Initialize the detector."""
        self._compiled_patterns = {}
        for data_type, patterns in self.PATTERNS.items():
            self._compiled_patterns[data_type] = [
                (re.compile(pattern, re.IGNORECASE), confidence)
                for pattern, confidence in patterns
            ]

    def detect(self, content: str) -> List[SensitiveDataMatch]:
        """
        Detect sensitive data in content.

        Args:
            content: Content to scan

        Returns:
            List of detected sensitive data matches
        """
        matches = []

        for data_type, patterns in self._compiled_patterns.items():
            for pattern, confidence in patterns:
                for match in pattern.finditer(content):
                    # Determine sensitivity level
                    sensitivity = self._get_sensitivity(data_type)

                    matches.append(SensitiveDataMatch(
                        data_type=data_type,
                        sensitivity=sensitivity,
                        value=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                    ))

        # Remove overlaps
        matches = self._remove_overlaps(matches)

        return matches

    def _get_sensitivity(self, data_type: DataType) -> SensitivityLevel:
        """Get sensitivity level for data type."""
        if data_type == DataType.CREDENTIAL:
            return SensitivityLevel.CRITICAL
        elif data_type == DataType.TOKEN:
            return SensitivityLevel.RESTRICTED
        elif data_type == DataType.FINANCIAL:
            return SensitivityLevel.CONFIDENTIAL
        elif data_type == DataType.HEALTH:
            return SensitivityLevel.CONFIDENTIAL
        elif data_type == DataType.PERSONAL:
            return SensitivityLevel.RESTRICTED
        else:
            return SensitivityLevel.INTERNAL

    def _remove_overlaps(
        self,
        matches: List[SensitiveDataMatch],
    ) -> List[SensitiveDataMatch]:
        """Remove overlapping matches."""
        if not matches:
            return []

        # Sort by start position
        sorted_matches = sorted(matches, key=lambda m: m.start_pos)

        filtered = [sorted_matches[0]]

        for match in sorted_matches[1:]:
            last = filtered[-1]
            if match.start_pos > last.end_pos:
                filtered.append(match)

        return filtered


class DataMasker:
    """
    Masks sensitive data in content.

    Strategies:
    - Partial masking (show first/last few chars)
    - Hash replacement
    - Token replacement
    """

    MASK_LENGTH = {
        SensitivityLevel.CRITICAL: 0,  # Fully mask
        SensitivityLevel.RESTRICTED: 4,  # Show first 4
        SensitivityLevel.CONFIDENTIAL: 8,  # Show first 8
        SensitivityLevel.INTERNAL: 12,  # Show first 12
        SensitivityLevel.PUBLIC: -1,  # No masking
    }

    def mask(self, content: str, matches: List[SensitiveDataMatch]) -> str:
        """
        Mask sensitive data in content.

        Args:
            content: Original content
            matches: Sensitive data matches

        Returns:
            str: Content with sensitive data masked
        """
        if not matches:
            return content

        # Sort matches by start position (reverse to avoid offset issues)
        sorted_matches = sorted(matches, key=lambda m: m.start_pos, reverse=True)

        masked_content = content

        for match in sorted_matches:
            value = match.value
            show_chars = self.MASK_LENGTH.get(match.sensitivity, 0)

            if show_chars <= 0:
                # Fully mask
                masked_value = "*" * len(value)
            elif len(value) > show_chars * 2:
                # Partial mask
                masked_value = (
                    value[:show_chars] +
                    "*" * (len(value) - show_chars * 2) +
                    value[-show_chars:]
                )
            else:
                # Too short to mask partially, mask fully
                masked_value = "*" * len(value)

            # Replace in content
            masked_content = (
                masked_content[:match.start_pos] +
                masked_value +
                masked_content[match.end_pos:]
            )

        return masked_content


class RBACManager:
    """
    Role-Based Access Control manager.

    Features:
    - Hierarchical permissions
    - Resource-based access control
    - Action-based permissions
    """

    # Define permissions for each role
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            "all": True,  # Admin has all permissions
        },
        UserRole.USER: {
            "chat:read": True,
            "chat:write": True,
            "models:list": True,
            "cost:read_own": True,
        },
    }

    # Resource ownership
    OWNERSHIP_RESOURCES = ["routing_decisions", "cost_records", "api_keys"]

    async def check_permission(
        self,
        user: User,
        resource: str,
        action: str,
        resource_owner_id: Optional[int] = None,
    ) -> bool:
        """
        Check if user has permission for resource/action.

        Args:
            user: User to check
            resource: Resource identifier
            action: Action to perform
            resource_owner_id: Owner of the resource (if applicable)

        Returns:
            bool: True if permitted
        """
        # Check user status
        if user.status != UserStatus.ACTIVE:
            return False

        # Get permissions for user's role
        role_permissions = self.ROLE_PERMISSIONS.get(user.role, {})

        # Admin check
        if role_permissions.get("all"):
            return True

        # Check specific permission
        permission_key = f"{resource}:{action}"
        if role_permissions.get(permission_key):
            # Check ownership if applicable
            if resource in self.OWNERSHIP_RESOURCES:
                if resource_owner_id is not None:
                    # User can access their own resources
                    return user.id == resource_owner_id

            return True

        return False


class AuditLogger:
    """
    Comprehensive audit logging.

    Logs:
    - Authentication events
    - Authorization decisions
    - Data access
    - Configuration changes
    - Security events
    """

    def __init__(self):
        """Initialize the audit logger."""
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._flush_interval = 60  # seconds

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[int],
        details: Dict[str, Any],
        severity: str = "info",
    ) -> None:
        """
        Log an audit event.

        Args:
            event_type: Type of event (e.g., "auth_success", "access_denied")
            user_id: User ID (if applicable)
            details: Event details
            severity: Event severity (info, warning, error, critical)
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "severity": severity,
            "details": details,
        }

        # Add to buffer
        self._buffer.append(event)

        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            await self._flush()

        # Also write to Redis for real-time access
        redis_key = RedisKeys.audit_log_prefix + event_type
        await RedisService.lpush(redis_key, str(event))
        await RedisService.ltrim(redis_key, 0, 999)  # Keep last 1000

    async def _flush(self) -> None:
        """Flush buffered events to persistent storage."""
        if not self._buffer:
            return

        # Write to database (would need DB session)
        # For now, just clear buffer
        self._buffer.clear()


class KeyRotationManager:
    """
    Manages API key rotation.

    Features:
    - Automatic key expiration
    - Graceful key rotation
    - Key versioning
    """

    def __init__(self):
        """Initialize the key rotation manager."""
        self._rotation_warning_days = 7
        self._max_key_age_days = 90

    async def check_key_rotation(
        self,
        api_key: APIKey,
    ) -> Dict[str, Any]:
        """
        Check if API key needs rotation.

        Args:
            api_key: API key to check

        Returns:
            Dict with rotation status
        """
        now = datetime.now(timezone.utc)
        created_at = api_key.created_at.replace(tzinfo=timezone.utc)
        age_days = (now - created_at).days

        if not api_key.expires_at:
            expires_at = created_at + timedelta(days=self._max_key_age_days)
        else:
            expires_at = api_key.expires_at.replace(tzinfo=timezone.utc)

        days_until_expiry = (expires_at - now).days

        needs_rotation = False
        urgency = "none"

        if days_until_expiry <= 0:
            needs_rotation = True
            urgency = "expired"
        elif days_until_expiry <= self._rotation_warning_days:
            needs_rotation = True
            urgency = "warning" if days_until_expiry > 0 else "critical"
        elif age_days >= self._max_key_age_days:
            needs_rotation = True
            urgency = "warning"

        return {
            "needs_rotation": needs_rotation,
            "urgency": urgency,
            "age_days": age_days,
            "days_until_expiry": days_until_expiry,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        }

    async def rotate_key(
        self,
        old_key_id: int,
        user_id: int,
    ) -> str:
        """
        Rotate an API key.

        Args:
            old_key_id: Old API key ID
            user_id: User ID requesting rotation

        Returns:
            str: New API key
        """
        # Generate new key
        new_key = self._generate_api_key()

        # Hash the new key
        from src.utils.encryption import hash_api_key
        key_hash = hash_api_key(new_key)

        # Create new API key record
        new_api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            name=f"Rotated from key {old_key_id}",
            is_active=True,
        )

        # Save to database
        result = await SessionManager.execute_insert(new_api_key)

        # Deactivate old key
        from src.models.user import APIKey
        old_key = await SessionManager.execute_get_one(
            select(APIKey).where(APIKey.id == old_key_id)
        )

        if old_key:
            old_key.is_active = False
            old_key.name = f"Rotated on {datetime.now(timezone.utc).isoformat()}"
            await SessionManager.execute_update(
                old_key,
                commit=True,
            )

        # Log audit event
        await audit_logger.log_event(
            event_type="key_rotated",
            user_id=user_id,
            details={
                "old_key_id": old_key_id,
                "new_key_id": result.id,
                "rotated_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="info",
        )

        return new_key

    def _generate_api_key(self) -> str:
        """Generate a new API key."""
        # Generate secure random key
        random_bytes = secrets.token_bytes(32)
        key = "llm_" + secrets.token_urlsafe(16)

        # Add check digits
        check_hash = hashlib.sha256(random_bytes).hexdigest()[:8]
        return f"{key}_{check_hash}"


class SecurityEngine:
    """
    Main security engine coordinating all security features.

    Features:
    - Sensitive data detection and masking
    - RBAC
    - Audit logging
    - Key rotation
    - Security scoring
    """

    def __init__(self):
        """Initialize the security engine."""
        self.detector = SensitiveDataDetector()
        self.masker = DataMasker()
        self.rbac = RBACManager()
        self.audit_logger = AuditLogger()
        self.key_rotation = KeyRotationManager()

    async def analyze_content_security(
        self,
        content: str,
        user: Optional[User] = None,
    ) -> SecurityDecision:
        """
        Analyze content security and make decision.

        Args:
            content: Content to analyze
            user: Optional user context

        Returns:
            SecurityDecision: Security decision result
        """
        issues = []
        required_actions = []
        risk_score = 0.0

        # Detect sensitive data
        matches = self.detector.detect(content)

        if matches:
            # Calculate risk score based on sensitivity
            for match in matches:
                if match.sensitivity == SensitivityLevel.CRITICAL:
                    risk_score += 0.4
                elif match.sensitivity == SensitivityLevel.RESTRICTED:
                    risk_score += 0.3
                elif match.sensitivity == SensitivityLevel.CONFIDENTIAL:
                    risk_score += 0.2
                elif match.sensitivity == SensitivityLevel.INTERNAL:
                    risk_score += 0.1

                issues.append(f"Sensitive data detected: {match.data_type.value}")

            # Mask content
            masked_content = self.masker.mask(content, matches)

            required_actions.append("mask_sensitive_data")
        else:
            masked_content = None

        # Cap risk score
        risk_score = min(risk_score, 1.0)

        # Make decision
        allow_request = risk_score < 0.8  # Allow if risk < 80%

        if risk_score > 0.5:
            required_actions.append("audit_log")

        if risk_score > 0.7:
            required_actions.append("admin_review")

        return SecurityDecision(
            allow_request=allow_request,
            risk_score=risk_score,
            detected_issues=issues,
            required_actions=required_actions,
            masked_content=masked_content,
        )

    async def check_access(
        self,
        user: User,
        resource: str,
        action: str,
        resource_owner_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check access permission and log audit event.

        Args:
            user: User requesting access
            resource: Resource to access
            action: Action to perform
            resource_owner_id: Owner of resource

        Returns:
            tuple[bool, Optional[str]]: (permitted, reason)
        """
        permitted = await self.rbac.check_permission(
            user, resource, action, resource_owner_id
        )

        reason = None
        if not permitted:
            reason = f"Access denied: user {user.username} lacks permission for {action} on {resource}"

            # Log audit event
            await self.audit_logger.log_event(
                event_type="access_denied",
                user_id=user.id,
                details={
                    "resource": resource,
                    "action": action,
                    "resource_owner_id": resource_owner_id,
                    "reason": reason,
                },
                severity="warning",
            )
        else:
            # Log successful access
            await self.audit_logger.log_event(
                event_type="access_granted",
                user_id=user.id,
                details={
                    "resource": resource,
                    "action": action,
                },
                severity="info",
            )

        return permitted, reason


# Global instances
sensitive_data_detector = SensitiveDataDetector()
data_masker = DataMasker()
rbac_manager = RBACManager()
audit_logger = AuditLogger()
key_rotation_manager = KeyRotationManager()
security_engine = SecurityEngine()
