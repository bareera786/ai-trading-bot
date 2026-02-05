"""Service for managing Resellers and their sub-users."""
from __future__ import annotations

from typing import Optional
from app.extensions import db
from app.models import Reseller, User


class ResellerService:
    @staticmethod
    def create_reseller(name: str, owner_id: str, limits_config: Optional[dict] = None) -> Reseller:
        """Create a new reseller account."""
        if Reseller.query.filter_by(name=name).first():
            raise ValueError(f"Reseller with name '{name}' already exists.")
            
        reseller = Reseller(
            name=name,
            owner_id=owner_id,
            limits_config=limits_config or {"max_users": 50, "max_bots_per_user": 5}
        )
        db.session.add(reseller)
        db.session.flush()  # Ensure ID is generated
        
        # Update owner to be the 'owner' of this reseller
        owner = db.session.get(User, owner_id)
        if owner:
            owner.reseller_id = reseller.id
            owner.reseller_role = "owner"
            
        db.session.commit()
        return reseller

    @staticmethod
    def assign_user_to_reseller(user_id: str, reseller_id: str) -> User:
        """Assign a user to a reseller, enforcing limits."""
        user = db.session.get(User, user_id)
        reseller = db.session.get(Reseller, reseller_id)

        if not user:
            raise ValueError("User not found")
        if not reseller:
            raise ValueError("Reseller not found")

        # Check global user limit for this reseller
        current_count = User.query.filter_by(reseller_id=reseller_id).count()
        max_users = reseller.limits_config.get("max_users", 50)

        if current_count >= max_users:
            raise ValueError(f"Reseller limit reached ({max_users} users max).")

        user.reseller_id = reseller.id
        user.reseller_role = "user"  # Default role
        db.session.commit()
        return user

    @staticmethod
    def remove_user_from_reseller(user_id: str) -> User:
        """Remove a user from their reseller."""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
            
        user.reseller_id = None
        user.reseller_role = "user"
        db.session.commit()
        return user
