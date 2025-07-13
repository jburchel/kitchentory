from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm

from .models import User, Household


class CustomSignupForm(SignupForm):
    """Custom signup form that includes additional fields."""

    first_name = forms.CharField(
        max_length=30,
        label=_("First Name"),
        widget=forms.TextInput(
            attrs={"placeholder": _("First Name"), "class": "form-input"}
        ),
    )

    last_name = forms.CharField(
        max_length=30,
        label=_("Last Name"),
        widget=forms.TextInput(
            attrs={"placeholder": _("Last Name"), "class": "form-input"}
        ),
    )

    household_invite_code = forms.CharField(
        max_length=20,
        required=False,
        label=_("Household Invite Code"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Optional: Enter invite code"),
                "class": "form-input",
            }
        ),
        help_text=_(
            "If you have an invite code from an existing household, enter it here."
        ),
    )

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        # Handle household invite code
        invite_code = self.cleaned_data.get("household_invite_code")
        if invite_code:
            try:
                household = Household.objects.get(invite_code=invite_code)
                user.household = household
                user.is_household_admin = False  # New members are not admins by default
            except Household.DoesNotExist:
                pass  # Silently ignore invalid invite codes

        user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "date_of_birth",
            "dietary_restrictions",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "dietary_restrictions": forms.TextInput(
                attrs={
                    "placeholder": _("e.g., vegetarian, gluten-free"),
                    "class": "form-input",
                    "data-role": "tagsinput",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = "form-input"


class HouseholdForm(forms.ModelForm):
    """Form for creating or updating a household."""

    class Meta:
        model = Household
        fields = ["name", "timezone", "currency"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": _("e.g., Smith Family"), "class": "form-input"}
            ),
            "timezone": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add timezone choices
        import pytz

        timezone_choices = [(tz, tz) for tz in pytz.all_timezones]
        self.fields["timezone"].widget = forms.Select(
            choices=timezone_choices, attrs={"class": "form-select"}
        )

        # Add currency choices
        currency_choices = [
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("GBP", "British Pound"),
            ("CAD", "Canadian Dollar"),
            ("AUD", "Australian Dollar"),
            ("JPY", "Japanese Yen"),
            ("CNY", "Chinese Yuan"),
            ("INR", "Indian Rupee"),
        ]
        self.fields["currency"].widget = forms.Select(
            choices=currency_choices, attrs={"class": "form-select"}
        )


class JoinHouseholdForm(forms.Form):
    """Form for joining an existing household."""

    invite_code = forms.CharField(
        max_length=20,
        label=_("Invite Code"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter household invite code"),
                "class": "form-input",
            }
        ),
    )

    def clean_invite_code(self):
        invite_code = self.cleaned_data["invite_code"]
        try:
            self.household = Household.objects.get(invite_code=invite_code)
        except Household.DoesNotExist:
            raise forms.ValidationError(_("Invalid invite code."))
        return invite_code
