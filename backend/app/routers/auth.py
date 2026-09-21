from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user
from app.models import Role, User
from app.schemas import GoogleLoginRequest, TokenResponse, UserRead
from app.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    if not settings.google_client_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Google client id not configured")

    try:
        claims = google_id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google token") from exc

    google_sub = claims["sub"]
    email = claims.get("email", "").lower()
    name = claims.get("name", email)
    picture = claims.get("picture")

    user = session.exec(select(User).where(User.google_sub == google_sub)).first()
    is_new_user = user is None
    if user is None:
        # New user registration. Grant admin role only if the email is on the allow-list.
        role = Role.admin if email in settings.admin_email_set else Role.customer
        user = User(google_sub=google_sub, email=email, name=name, picture=picture, role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        # Existing user login: keep profile fields fresh, and promote to admin if their
        # email was added to the allow-list after their account was created. Never
        # demotes automatically - removing an email from the list doesn't strip an
        # existing admin's access.
        user.name = name
        user.picture = picture
        if email in settings.admin_email_set and user.role != Role.admin:
            user.role = Role.admin
        session.add(user)
        session.commit()
        session.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user), is_new_user=is_new_user)


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)
