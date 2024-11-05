from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Length
from email_validator import validate_email, EmailNotValidError



class EmailValidator:
    def __init__(self, message=None):
        if not message:
            message = "Invalid email address."
        self.message = message

    def __call__(self, form, field):
        try:
            # Validate the email
            validate_email(field.data)
        except EmailNotValidError as e:
            # Raise a validation error with the original error message
            raise ValueError(f"{self.message}: {str(e)}") from e

class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[DataRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), EmailValidator()])
    password = PasswordField('Password', validators=[Length(min=6)])
    image_url = StringField('(Optional) Image URL')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])


class ProfileEditForm(FlaskForm):
    """Form for editing user profile."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), EmailValidator()])
    image_url = StringField('(Optional) Profile Image URL')
    header_image_url = StringField('(Optional) Header Image URL')
    bio = TextAreaField('Bio')
    location = StringField('Location')
    password = PasswordField('Password', validators=[Length(min=6)])


class ChangePasswordForm(FlaskForm):
    """Change Password form."""

    password = PasswordField('Current Password', validators=[Length(min=6)])
    new_password = PasswordField('New Password', validators=[Length(min=6)])
    new_password_match = PasswordField('New Password Again', validators=[Length(min=6)])

    def validate(self):
        # Call the base validate method first
        if not super().validate():
            return False
        # Check if new passwords match
        if self.new_password.data != self.new_password_match.data:
            self.new_password_match.errors.append("New passwords must match.")
            return False
        return True
