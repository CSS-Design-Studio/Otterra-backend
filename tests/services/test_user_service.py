import pytest
from unittest.mock import MagicMock, patch
from app.services.user_service import UserService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def svc(mock_repo):
    return UserService(user_repository=mock_repo)


@pytest.fixture
def sample_user():
    return {
        "id": "user-1",
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "$2b$12$hashedpassword",
        "first_name": "Test",
        "last_name": "User",
        "role_id": "customer",
        "is_suspended": False,
    }


class TestCreateUser:
    def test_success(self, svc, mock_repo):
        mock_repo.exists_by_email.return_value = False
        mock_repo.exists_by_username.return_value = False
        mock_repo.create.return_value = {
            "id": "user-1",
            "email": "new@example.com",
            "username": "newuser",
            "password_hash": "hashed",
        }

        result = svc.create_user({
            "email": "new@example.com",
            "password": "secret123",
            "username": "newuser",
        })

        assert result["email"] == "new@example.com"
        assert "password_hash" not in result
        mock_repo.create.assert_called_once()

    def test_missing_email_raises(self, svc):
        with pytest.raises(ValueError, match="Email not provided"):
            svc.create_user({"password": "secret"})

    def test_duplicate_email_raises(self, svc, mock_repo):
        mock_repo.exists_by_email.return_value = True
        with pytest.raises(ValueError, match="Email already exists"):
            svc.create_user({"email": "dup@example.com", "password": "secret"})

    def test_duplicate_username_raises(self, svc, mock_repo):
        mock_repo.exists_by_email.return_value = False
        mock_repo.exists_by_username.return_value = True
        with pytest.raises(ValueError, match="Username already exists"):
            svc.create_user({"email": "x@example.com", "password": "s", "username": "taken"})

    def test_default_username_from_email(self, svc, mock_repo):
        mock_repo.exists_by_email.return_value = False
        mock_repo.create.return_value = {"id": "u1", "email": "foo@bar.com", "username": "foo"}

        svc.create_user({"email": "foo@bar.com", "password": "secret"})
        create_call = mock_repo.create.call_args[0][0]
        assert create_call["username"] == "foo"


class TestAuthenticateUser:
    def test_success(self, svc, mock_repo, sample_user):
        mock_repo.find_by_email.return_value = sample_user.copy()
        with patch.object(svc, "verify_password", return_value=True):
            result = svc.authenticate_user("test@example.com", "password")
        assert result is not None
        assert "password_hash" not in result

    def test_user_not_found(self, svc, mock_repo):
        mock_repo.find_by_email.return_value = None
        result = svc.authenticate_user("no@example.com", "password")
        assert result is None

    def test_wrong_password(self, svc, mock_repo, sample_user):
        mock_repo.find_by_email.return_value = sample_user.copy()
        with patch.object(svc, "verify_password", return_value=False):
            result = svc.authenticate_user("test@example.com", "wrong")
        assert result is None


class TestLogin:
    def test_success_returns_tokens(self, svc):
        with patch.object(svc, "authenticate_user", return_value={"id": "user-1", "role_id": "customer"}):
            result = svc.login({"email": "test@example.com", "password": "pass"})
        assert "access_token" in result
        assert "refresh_token" in result

    def test_failure_returns_none(self, svc):
        with patch.object(svc, "authenticate_user", return_value=None):
            result = svc.login({"email": "bad@example.com", "password": "wrong"})
        assert result is None

    def test_missing_fields_returns_none(self, svc):
        result = svc.login({})
        assert result is None


class TestGetUserById:
    def test_found(self, svc, mock_repo, sample_user):
        mock_repo.find_by_id.return_value = sample_user.copy()
        result = svc.get_user_by_id("user-1")
        assert result["id"] == "user-1"
        assert "password_hash" not in result

    def test_not_found(self, svc, mock_repo):
        mock_repo.find_by_id.return_value = None
        result = svc.get_user_by_id("nonexistent")
        assert result is None


class TestUpdateUser:
    def test_update_fields(self, svc, mock_repo):
        mock_repo.update.return_value = {"id": "u1", "first_name": "New", "password_hash": "h"}
        result = svc.update_user("u1", {"first_name": "New"})
        assert result["first_name"] == "New"
        assert "password_hash" not in result

    def test_update_password_gets_hashed(self, svc, mock_repo):
        mock_repo.update.return_value = {"id": "u1", "password_hash": "new_hash"}
        svc.update_user("u1", {"password": "newpass123"})
        call_data = mock_repo.update.call_args[0][1]
        assert "password" not in call_data
        assert "password_hash" in call_data


class TestDeleteUser:
    def test_success(self, svc, mock_repo):
        mock_repo.delete.return_value = True
        assert svc.delete_user("user-1") is True

    def test_not_found(self, svc, mock_repo):
        mock_repo.delete.return_value = False
        assert svc.delete_user("nonexistent") is False


class TestOAuthLogin:
    @patch("app.services.user_service.google_id_token.verify_oauth2_token")
    def test_google_existing_user(self, mock_verify, svc, mock_repo):
        mock_verify.return_value = {
            "email": "test@gmail.com",
            "sub": "google-123",
            "name": "Test User",
        }
        mock_repo.find_by_email.return_value = {"id": "user-1", "email": "test@gmail.com"}

        result = svc.oauth_login("google", "fake-id-token")
        assert "access_token" in result
        assert "refresh_token" in result
        mock_repo.create.assert_not_called()

    @patch("app.services.user_service.google_id_token.verify_oauth2_token")
    def test_google_new_user(self, mock_verify, svc, mock_repo):
        mock_verify.return_value = {
            "email": "new@gmail.com",
            "sub": "google-456",
            "name": "New User",
        }
        mock_repo.find_by_email.return_value = None
        mock_repo.create.return_value = {"id": "user-2", "email": "new@gmail.com"}

        result = svc.oauth_login("google", "fake-id-token")
        assert "access_token" in result
        mock_repo.create.assert_called_once()

    @patch("app.services.user_service.google_id_token.verify_oauth2_token")
    def test_invalid_google_token_raises(self, mock_verify, svc):
        mock_verify.side_effect = ValueError("bad token")
        with pytest.raises(ValueError, match="Invalid Google token"):
            svc.oauth_login("google", "bad-token")

    def test_unsupported_provider_raises(self, svc):
        with pytest.raises(ValueError, match="Unsupported provider"):
            svc.oauth_login("apple", "some-token")


class TestGetAllUsers:
    def test_returns_list_without_passwords(self, svc, mock_repo):
        mock_repo.find_all.return_value = [
            {"id": "u1", "email": "a@b.com", "password_hash": "h1"},
            {"id": "u2", "email": "c@d.com", "password_hash": "h2"},
        ]
        result = svc.get_all_users()
        assert len(result) == 2
        for user in result:
            assert "password_hash" not in user
