from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.scheme import Scheme, SchemeNotificationPreference
from app.models.user import User


async def create_due_scheme_notifications(db: AsyncSession, user: Optional[User] = None) -> None:
    today = date.today()
    window_end = today + timedelta(days=30)
    stmt = (
        select(SchemeNotificationPreference, Scheme, User)
        .join(Scheme, Scheme.id == SchemeNotificationPreference.scheme_id)
        .join(User, User.id == SchemeNotificationPreference.user_id)
        .where(
            Scheme.deadline >= today,
            Scheme.deadline <= window_end,
            Scheme.status != "closed",
        )
        .with_for_update(of=SchemeNotificationPreference)
    )
    if user is not None:
        stmt = stmt.where(SchemeNotificationPreference.user_id == user.id)
    rows = (await db.execute(stmt)).all()
    created = False
    for preference, scheme, notification_user in rows:
        if preference.notified_deadline == scheme.deadline:
            continue
        if notification_user.language == "hi":
            message = f"{scheme.name_hi or scheme.name} की समय-सीमा {scheme.deadline.isoformat()} को है। आधिकारिक पोर्टल पर पुष्टि करें।"
        elif notification_user.language == "mr":
            message = f"{scheme.name_mr or scheme.name} ची अंतिम तारीख {scheme.deadline.isoformat()} आहे. अधिकृत पोर्टलवर खात्री करा."
        else:
            message = f"{scheme.name} has a deadline on {scheme.deadline.isoformat()}. Confirm details on the official portal."
        db.add(Notification(user_id=notification_user.id, type="alert", message=message))
        preference.notified_deadline = scheme.deadline
        created = True
    if created:
        await db.commit()
