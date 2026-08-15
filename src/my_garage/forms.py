"""Django forms for my_garage."""

import json

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateExecutor,
    GenericServiceRecord,
    GenericUpgrade,
)

# AUTHENTICATION FORMS
# ============================================================================


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, help_text="Required. Used for password reset."
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "email@example.com",
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First name",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Last name",
                    "autocomplete": "family-name",
                }
            ),
        }


# ESTATE & LEGACY FORMS
# ============================================================================


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ["name", "relationship", "contact_info", "notes"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name"}
            ),
            "relationship": forms.Select(attrs={"class": "form-control"}),
            "contact_info": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Email, phone, or address (optional)",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Any additional notes (optional)",
                }
            ),
        }


class EstateExecutorForm(forms.ModelForm):
    class Meta:
        model = EstateExecutor
        fields = ["name", "contact_info"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name"}
            ),
            "contact_info": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Email, phone, or address (optional)",
                }
            ),
        }


class BeneficiaryAssignmentForm(forms.ModelForm):
    class Meta:
        model = BeneficiaryAssignment
        fields = ["beneficiary", "conditional_note", "is_charitable", "charitable_org"]
        widgets = {
            "beneficiary": forms.Select(attrs={"class": "form-control"}),
            "conditional_note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Optional: describe any conditions on this bequest",
                }
            ),
            "charitable_org": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Organization name (if charitable)",
                }
            ),
        }

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields["beneficiary"].queryset = Beneficiary.objects.filter(
                owner=owner
            )
        self.fields["beneficiary"].required = False
        self.fields["beneficiary"].empty_label = "— Select beneficiary —"


class EstateActivateForm(forms.Form):
    confirmed = forms.BooleanField(
        required=True,
        label="I understand this code must be kept secure and cannot be recovered.",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        error_messages={"required": "You must confirm before activating."},
    )


# DYNAMIC COLLECTION SYSTEM FORMS
# ============================================================================


class CollectionTypeForm(forms.ModelForm):
    """
    Form for creating/editing collection types.
    The schema builder is handled via JavaScript on the frontend.
    """

    class Meta:
        model = CollectionType
        fields = ["name", "icon", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Wine Collection, Art Collection",
                }
            ),
            "icon": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., fa-wine-glass, fa-palette",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe this collection...",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "name": "Give your collection a name",
            "icon": "FontAwesome icon class (optional)",
            "description": "Optional description of this collection",
        }


class DynamicCollectionItemForm(forms.ModelForm):
    """
    Base form for collection items. Custom fields are added dynamically.
    """

    class Meta:
        model = DynamicCollectionItem
        fields = [
            "name",
            "photo",
            "purchase_price",
            "purchase_date",
            "current_market_value",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "photo": forms.FileInput(attrs={"class": "form-control"}),
            "purchase_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "purchase_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "current_market_value": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, collection_type=None, **kwargs):  # noqa: C901
        super().__init__(*args, **kwargs)

        # Field names whose comma-separated input is stored as a JSON array.
        # Populated below and consumed by save().
        self._json_list_fields: set[str] = set()

        if not collection_type:
            return

        # Add dynamic fields based on schema
        schema = collection_type.field_schema
        fields_list = schema.get("fields", [])

        for field_def in fields_list:
            # Skip system-managed fields — written by service providers, not user forms.
            if field_def.get("system") or field_def.get("type") == "system_json":
                continue

            field_name = field_def.get("name")
            field_type = field_def.get("type")

            # Also skip if the stored value is a complex type (dict/list), regardless
            # of whether the schema flags are set correctly in the DB.
            # json_list is exempt: a list is its *expected* storage form.
            if self.instance and self.instance.pk and field_type != "json_list":
                existing = self.instance.custom_fields.get(field_name)
                if isinstance(existing, (dict, list)):
                    continue

            label = field_def.get("label", field_name.replace("_", " ").title())
            required = field_def.get("required", False)
            help_text = field_def.get("help_text", "")

            # Create appropriate Django form field
            if field_type == "text":
                field = forms.CharField(
                    label=label,
                    required=required,
                    max_length=field_def.get("max_length", 200),
                    help_text=help_text,
                    widget=forms.TextInput(attrs={"class": "form-control"}),
                )
            elif field_type == "number":
                field = forms.DecimalField(
                    label=label,
                    required=required,
                    max_digits=10,
                    decimal_places=2,
                    help_text=help_text,
                    widget=forms.NumberInput(
                        attrs={"class": "form-control", "step": "0.01"}
                    ),
                )
            elif field_type == "date":
                field = forms.DateField(
                    label=label,
                    required=required,
                    help_text=help_text,
                    widget=forms.DateInput(
                        attrs={"class": "form-control", "type": "date"}
                    ),
                )
            elif field_type == "file":
                field = forms.FileField(
                    label=label,
                    required=required,
                    help_text=help_text,
                    widget=forms.FileInput(attrs={"class": "form-control"}),
                )
            elif field_type == "select":
                # Single-choice dropdown. Schema supplies [{"value", "label"}, ...].
                choices = [
                    (choice.get("value"), choice.get("label", choice.get("value")))
                    for choice in field_def.get("choices", [])
                ]
                if not required:
                    choices = [("", "———")] + choices
                field = forms.ChoiceField(
                    label=label,
                    required=required,
                    choices=choices,
                    help_text=help_text,
                    widget=forms.Select(attrs={"class": "form-control"}),
                )
            elif field_type == "boolean":
                # Checkboxes are never "required" in the HTML sense — a required
                # checkbox would force the user to tick it to submit the form.
                field = forms.BooleanField(
                    label=label,
                    required=False,
                    help_text=help_text,
                    widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
                )
            elif field_type == "json_list":
                # Comma-separated input, stored as a JSON array.
                suggestions = field_def.get("suggestions", [])
                attrs = {
                    "class": "form-control",
                    "placeholder": ", ".join(suggestions[:3]) if suggestions else "",
                }
                if suggestions:
                    attrs["data-suggestions"] = json.dumps(suggestions)
                field = forms.CharField(
                    label=label,
                    required=required,
                    help_text=help_text,
                    widget=forms.TextInput(attrs=attrs),
                )
                self._json_list_fields.add(field_name)
            elif field_type == "relationship":
                # Relationship to other collection items
                field = forms.ModelChoiceField(
                    label=label,
                    required=required,
                    help_text=help_text,
                    queryset=DynamicCollectionItem.objects.filter(
                        owner=collection_type.owner
                    ),
                    widget=forms.Select(attrs={"class": "form-control"}),
                )
            else:
                continue

            # Add the field with custom_ prefix
            self.fields[f"custom_{field_name}"] = field

            # Set initial value if editing
            if self.instance and self.instance.pk:
                initial_value = self.instance.custom_fields.get(field_name)
                if initial_value is not None:
                    if field_name in self._json_list_fields and isinstance(
                        initial_value, list
                    ):
                        initial_value = ", ".join(str(v) for v in initial_value)
                    self.fields[f"custom_{field_name}"].initial = initial_value

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Start from existing custom_fields so system-managed data (specs, features, etc.)  # noqa: E501
        # written by service providers is preserved across form saves.
        custom_data = dict(instance.custom_fields) if instance.custom_fields else {}

        # Overwrite only the fields actually present in this form (user-editable fields).  # noqa: E501
        for field_name in self.fields:
            if field_name.startswith("custom_"):
                actual_field_name = field_name.replace("custom_", "")
                value = self.cleaned_data.get(field_name)

                # Handle file fields specially
                if isinstance(self.fields[field_name], forms.FileField) and value:
                    # For file fields in custom_fields, we'll store the file path
                    # You might want to handle this differently (e.g., separate file storage)  # noqa: E501
                    custom_data[actual_field_name] = value.name
                elif (
                    isinstance(self.fields[field_name], forms.ModelChoiceField)
                    and value
                ):
                    # Store relationship as ID
                    custom_data[actual_field_name] = value.id
                elif actual_field_name in self._json_list_fields:
                    # Split comma-separated input into a JSON array, dropping blanks.
                    custom_data[actual_field_name] = [
                        part.strip()
                        for part in (value or "").split(",")
                        if part.strip()
                    ]
                else:
                    custom_data[actual_field_name] = value

        instance.custom_fields = custom_data

        if commit:
            instance.save()

        return instance


class GenericServiceRecordForm(forms.ModelForm):
    """Form for creating generic service records."""

    class Meta:
        model = GenericServiceRecord
        fields = [
            "date",
            "vendor",
            "description",
            "category",
            "total_cost",
            "receipt_image",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "vendor": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "total_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "receipt_image": forms.FileInput(attrs={"class": "form-control"}),
        }
        help_texts = {
            "receipt_image": "Upload receipt image for OCR processing",
        }


class GenericUpgradeForm(forms.ModelForm):
    """Form for creating generic upgrades."""

    class Meta:
        model = GenericUpgrade
        fields = [
            "name",
            "brand",
            "part_number",
            "status",
            "cost",
            "ordered_date",
            "completion_date",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "part_number": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "ordered_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "completion_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
