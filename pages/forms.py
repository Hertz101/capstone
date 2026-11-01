"""Forms for creating users together with their hunter profile."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import ChatGroup, HuntingMethod, Profile


class ProfileForm(forms.ModelForm):
    """Profile fields shown alongside the signup (and editable later)."""

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

    def clean_state(self):
        # Signup normalizes the state to upper case; the profile page must too.
        return self.cleaned_data.get("state", "").upper()


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
        user = super().save(commit=True)
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
