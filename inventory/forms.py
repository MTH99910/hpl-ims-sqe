"""
Inventory App - Forms for Item Management
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Item, Location, Transaction


class ItemForm(forms.ModelForm):
    """Form for creating and updating items"""
    
    class Meta:
        model = Item
        fields = [
            'material_code', 'description', 'item_type', 'unit_of_measurement',
            'location', 'quantity_total', 'reorder_level', 'is_active'
        ]
        widgets = {
            'material_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ST001, HK001'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detailed item description'
            }),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'unit_of_measurement': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'quantity_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_material_code(self):
        """Validate material code format and uniqueness"""
        code = self.cleaned_data['material_code'].upper()
        existing = Item.objects.filter(material_code=code).exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError(f"Material code '{code}' already exists.")
        return code
    
    def clean_quantity_total(self):
        """Ensure quantity is non-negative"""
        qty = self.cleaned_data['quantity_total']
        if qty < 0:
            raise ValidationError("Quantity cannot be negative.")
        return qty
    
    def clean_reorder_level(self):
        """Ensure reorder level is non-negative"""
        level = self.cleaned_data['reorder_level']
        if level < 0:
            raise ValidationError("Reorder level cannot be negative.")
        return level


class LocationForm(forms.ModelForm):
    """Form for creating and updating locations"""
    
    class Meta:
        model = Location
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_code(self):
        """Ensure code is uppercase and unique"""
        code = self.cleaned_data['code'].upper()
        existing = Location.objects.filter(code=code).exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError(f"Location code '{code}' already exists.")
        return code


class StockAdjustmentForm(forms.ModelForm):
    """Form for adjusting stock quantities"""
    
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'quantity_change', 'notes']
        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updateQuantityDisplay()'
            }),
            'quantity_change': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quantity (positive or negative)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Reason for adjustment'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        qty_change = cleaned_data.get('quantity_change')
        txn_type = cleaned_data.get('transaction_type')
        
        if qty_change is None:
            return cleaned_data
        
        if txn_type in ['outward', 'write_off']:
            # Ensure sufficient stock for outward transactions
            if self.item and abs(qty_change) > self.item.quantity_total:
                raise ValidationError({
                    'quantity_change': f'Insufficient stock. Available: {self.item.quantity_total}'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.item = self.item
        transaction.user = self.initial.get('user')
        transaction.reference = self.initial.get('reference')
        
        # Calculate balance after
        if self.item:
            transaction.balance_after = self.item.quantity_total + transaction.quantity_change
            if commit:
                transaction.save()
                # Update item quantity
                self.item.quantity_total = transaction.balance_after
                self.item.save()
        
        return transaction


class ItemSearchForm(forms.Form):
    """Form for searching items"""
    search_type = forms.ChoiceField(
        choices=[
            ('code', 'Material Code'),
            ('description', 'Description'),
            ('type', 'Item Type'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search...'
        })
    )
