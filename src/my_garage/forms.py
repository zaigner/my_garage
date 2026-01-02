"""Django forms for my_garage."""
from django import forms
from my_garage.models import Vehicle, ServiceRecord, Upgrade


class VehicleForm(forms.ModelForm):
    """Form for creating/updating vehicles."""

    class Meta:
        model = Vehicle
        fields = ['make', 'model', 'year', 'trim', 'vin', 'purchase_price', 'mileage']
        widgets = {
            'year': forms.NumberInput(attrs={'min': 1900, 'max': 2100, 'class': 'form-control'}),
            'mileage': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'trim': forms.TextInput(attrs={'class': 'form-control'}),
            'vin': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 17}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        help_texts = {
            'vin': '17-character Vehicle Identification Number',
            'purchase_price': 'Original purchase price in USD',
        }


class ServiceRecordForm(forms.ModelForm):
    """Form for creating service records."""

    class Meta:
        model = ServiceRecord
        fields = ['date', 'vendor', 'description', 'category', 'total_cost', 'receipt_image']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'total_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'receipt_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'receipt_image': 'Upload receipt image for OCR processing',
        }


class UpgradeForm(forms.ModelForm):
    """Form for creating upgrades."""

    class Meta:
        model = Upgrade
        fields = ['part_name', 'brand', 'part_number', 'status', 'cost', 'installation_date', 'notes']
        widgets = {
            'part_name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'part_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        help_texts = {
            'part_number': 'Manufacturer part number (optional)',
            'installation_date': 'Date installed (leave blank if not yet installed)',
        }
