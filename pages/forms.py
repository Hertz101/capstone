"""Forms for creating users together with their hunter profile."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import ChatGroup, HuntingMethod, Profile


class ProfileForm(forms.ModelForm):
    """Profile fields shown alongside the signup (and editable later)."""

    # Lives on User, not Profile — surfaced here so users can add or fix the
    # address that group-chat notifications are sent to.
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        help_text="Used to notify you when someone posts or likes in your groups.",
    )

    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "city", "state", "method", "photo"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "2", "placeholder": "CO"}
            ),
            "method": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        # Pre-fill the email from the linked User, and remember it for save().
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user and not self.is_bound:
            self.fields["email"].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        # Sharing an inbox between accounts is allowed (a couple using one
        # address both get notified). If this account already had a UNIQUE
        # address and you're claiming one others use, just note it.
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk if self.user else None)
        if qs.exists():
            self.shared_with = list(qs.values_list("username", flat=True))
        else:
            self.shared_with = []
        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if self.user:
            self.user.email = self.cleaned_data["email"]
            self.user.save(update_fields=["email"])
        return profile

    def clean_state(self):
        # Signup normalizes the state to upper case; profile must too.
        # Server-side check: the widget's maxlength is client-side only.
        state = self.cleaned_data.get("state", "").upper()
        if state and (len(state) != 2 or not state.isalpha()):
            raise forms.ValidationError(
                "State must be a 2-letter code (e.g. CO)."
            )
        return state


class ChatGroupForm(forms.ModelForm):
    """Create a group and pick the users to add to it."""

    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "8"}),
        help_text="Hold Ctrl/Cmd to select multiple users",
    )

    class Meta:
        model = ChatGroup
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Camp crew 2026"})}

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)
        # You can add any registered user; you're added as a member automatically.
        qs = User.objects.all()
        if current_user:
            qs = qs.exclude(pk=current_user.pk)
        self.fields["members"].queryset = qs

    def save(self, commit=True):
        group = super().save(commit=False)
        group.created_by = self.current_user
        group.save()
        if self.current_user:
            group.members.add(self.current_user)
        group.members.add(*self.cleaned_data.get("members", []))
        return group


class SignupForm(UserCreationForm):
    """UserCreationForm plus the hunter profile fields on one page."""

    # Required so group-chat notification emails have somewhere to go.
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        help_text="Used to notify you when someone posts or likes in your groups.",
    )
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=2, required=False)
    method = forms.ChoiceField(
        choices=[("", "— Choose —")] + list(HuntingMethod.choices),
        required=False,
    )
    photo = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "city", "state"):
            self.fields[name].widget.attrs.update({"class": "form-control"})
        self.fields["state"].widget.attrs.update({"placeholder": "CO"})
        self.fields["method"].widget.attrs.update({"class": "form-select"})
        self.fields["photo"].widget.attrs.update({"class": "form-control", "accept": "image/*"})

    def save(self, commit=True):
        user = super().save(commit=False)
        # UserCreationForm doesn't persist the email field automatically;
        # it has to be copied from cleaned_data before the user is saved.
        user.email = self.cleaned_data["email"]
        user.save()
        data = self.cleaned_data
        Profile.objects.create(
            user=user,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            city=data.get("city", ""),
            state=data.get("state", "").upper(),
            method=data.get("method") or "",
            photo=data.get("photo"),
        )
        return user
