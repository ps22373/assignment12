import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserUpdate, PasswordUpdate


def valid_user_data():
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "username": "johndoe",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }


# UserCreate password validation
@pytest.mark.parametrize(
    "password, expected_error",
    [
        ("securepass123!", "uppercase"),
        ("SECUREPASS123!", "lowercase"),
        ("SecurePassword!", "digit"),
        ("SecurePass123", "special character"),
    ],
)
def test_user_create_rejects_weak_password(password, expected_error):
    data = valid_user_data()
    data["password"] = password
    data["confirm_password"] = password

    with pytest.raises(ValidationError, match=expected_error):
        UserCreate(**data)


def test_user_create_rejects_mismatched_passwords():
    data = valid_user_data()
    data["confirm_password"] = "DifferentPass123!"

    with pytest.raises(ValidationError, match="Passwords do not match"):
        UserCreate(**data)


# UserUpdate validation
def test_user_update_accepts_valid_optional_fields():
    user = UserUpdate(
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        username="janesmith",
    )

    assert user.first_name == "Jane"
    assert user.email == "jane@example.com"


def test_user_update_accepts_empty_update():
    user = UserUpdate()
    assert user.first_name is None
    assert user.last_name is None
    assert user.email is None
    assert user.username is None


def test_user_update_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserUpdate(email="not-an-email")


def test_user_update_rejects_short_username():
    with pytest.raises(ValidationError):
        UserUpdate(username="ab")


# PasswordUpdate validation
def test_password_update_rejects_mismatched_passwords():
    with pytest.raises(
        ValidationError,
        match="New password and confirmation do not match",
    ):
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass123!",
            confirm_new_password="DifferentPass123!",
        )


def test_password_update_rejects_reusing_current_password():
    with pytest.raises(
        ValidationError,
        match="New password must be different from current password",
    ):
        PasswordUpdate(
            current_password="SamePass123!",
            new_password="SamePass123!",
            confirm_new_password="SamePass123!",
        )


def test_password_update_accepts_valid_password_change():
    update = PasswordUpdate(
        current_password="OldPass123!",
        new_password="NewPass123!",
        confirm_new_password="NewPass123!",
    )

    assert update.new_password == "NewPass123!"