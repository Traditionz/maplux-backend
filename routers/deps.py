from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from domain.user.models import User
from security.authentication import (
    get_admin_user,
    get_current_user,
    get_current_user_allow_unactivated,
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserAllowUnactivated = Annotated[User, Depends(get_current_user_allow_unactivated)]
AdminUser = Annotated[User, Depends(get_admin_user)]
