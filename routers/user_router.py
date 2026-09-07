from fastapi import APIRouter, HTTPException, status

from domain import address, user, user_image, user_suspension
from domain.address.schemas import AddressBaseSchema, AddressCreateSchema
from domain.user.schemas import (
    StatusMessageSchema,
    SuspensionCreateSchema,
    UserBaseSchema,
    UserPublicSchema,
    UserUpdateSchema,
)
from domain.user_image.schemas import UserImageBaseSchema, UserImageCreateSchema
from routers.deps import AdminUser, CurrentUser, DbSession

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserBaseSchema)
async def read_current_user(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserBaseSchema)
async def update_current_user(
    updates: UserUpdateSchema,
    current_user: CurrentUser,
    db: DbSession,
):
    updated = user.repository.update_user_profile(db, current_user.user_id, updates)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return updated


@router.get("/me/address", response_model=AddressBaseSchema)
async def read_current_user_address(current_user: CurrentUser, db: DbSession):
    db_address = address.repository.get_address(db=db, user_id=current_user.user_id)
    if db_address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    return db_address


@router.put("/me/address", response_model=AddressBaseSchema)
async def upsert_current_user_address(
    new_address: AddressCreateSchema,
    current_user: CurrentUser,
    db: DbSession,
):
    return address.repository.upsert_address(
        db=db, user_id=current_user.user_id, address=new_address
    )


@router.get("/me/image", response_model=UserImageBaseSchema)
async def read_current_user_image(current_user: CurrentUser, db: DbSession):
    db_user_image = user_image.repository.get_user_image(db=db, user_id=current_user.user_id)
    if db_user_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User image not found.")
    return db_user_image


@router.put("/me/image", response_model=UserImageBaseSchema)
async def upsert_current_user_image(
    user_image_update: UserImageCreateSchema,
    current_user: CurrentUser,
    db: DbSession,
):
    return user_image.repository.upsert_user_image(
        db=db,
        user_id=current_user.user_id,
        user_image=user_image_update,
    )


@router.get("/{user_id}", response_model=UserPublicSchema)
async def get_user(user_id: int, _: CurrentUser, db: DbSession):
    db_user = user.repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return db_user


@router.post("/{user_id}/suspensions", response_model=StatusMessageSchema)
async def suspend_user(
    user_id: int,
    payload: SuspensionCreateSchema,
    _: AdminUser,
    db: DbSession,
):
    db_user = user.repository.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.duration_days >= 36525:
        user_suspension.repository.create_user_suspension_indefinite(db=db, user_id=user_id)
    else:
        user_suspension.repository.create_user_suspension_short(
            db=db, user_id=user_id, days=payload.duration_days
        )
    return StatusMessageSchema(
        status="success",
        message=f"User has been suspended for {payload.duration_days} days.",
    )
