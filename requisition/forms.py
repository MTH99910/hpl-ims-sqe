"""
Requisition App - Forms for Requisition Workflow
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Requisition, RequisitionLineItem
from inventory.models import Item


class RequisitionCreateForm(forms.ModelForm):
    """Form for creating requisitions"""
    
    class Meta:
        model = Requisition
        fields = ['purpose', 'notes']
        widgets = {
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter the purpose of this requisition...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any additional notes (optional)'
            }),
        }


class RequisitionLineItemForm(forms.ModelForm):
    """Form for individual line items in a requisition"""
    
    class Meta:
        model = RequisitionLineItem
        fields = ['item', 'quantity_requested', 'uom', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_requested': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'uom': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = Item.objects.filter(is_active=True)
        self.fields['item'].empty_label = "Select an item..."
    
    def clean_quantity_requested(self):
        """Ensure quantity is positive and doesn't exceed available stock"""
        qty = self.cleaned_data['quantity_requested']
        item = self.cleaned_data.get('item')
        
        if qty < 1:
            raise ValidationError("Quantity must be at least 1.")
        
        if item and qty > item.quantity_total:
            raise ValidationError(
                f"Requested quantity ({qty}) exceeds available stock ({item.quantity_total})."
            )
        
        return qty


class RequisitionLineItemUpdateForm(forms.ModelForm):
    """Form for updating line item quantities (used by Admin when issuing items)"""
    
    class Meta:
        model = RequisitionLineItem
        fields = ['quantity_issued', 'notes']
        widgets = {
            'quantity_issued': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Enter quantity to issue'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default quantity_issued to quantity_requested
        if self.instance and self.instance.pk:
            if self.instance.quantity_issued == 0:
                self.initial['quantity_issued'] = self.instance.quantity_requested
    
    def clean_quantity_issued(self):
        """Validate issued quantity doesn't exceed requested or available"""
        qty_issued = self.cleaned_data['quantity_issued']
        item = self.instance.item
        qty_requested = self.instance.quantity_requested
        
        if qty_issued < 0:
            raise ValidationError("Issued quantity cannot be negative.")
        
        if qty_issued > qty_requested:
            raise ValidationError(
                f"Cannot issue more than requested ({qty_requested})."
            )
        
        if item and qty_issued > item.quantity_total:
            raise ValidationError(
                f"Insufficient stock. Available: {item.quantity_total}, Requested: {qty_requested}."
            )
        
        return qty_issued


class HODActionForm(forms.ModelForm):
    """Form for HOD approval/rejection/send back"""
    
    ACTION_CHOICES = [
        ('authorized', 'Authorize'),
        ('sent_back', 'Send Back for Revision'),
        ('rejected', 'Reject'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Action',
        help_text='Select your action for this requisition'
    )
    
    class Meta:
        model = Requisition
        fields = ['status', 'notes', 'rejection_reason', 'sent_back_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select', 'style': 'display: none;'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional notes (optional)'
            }),
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for rejection (required if rejecting)'
            }),
            'sent_back_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Please provide comments explaining what needs to be revised (required if sending back)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide the status field as we'll set it based on action
        self.fields['status'].widget.attrs['style'] = 'display: none;'
        self.fields['rejection_reason'].required = False
        self.fields['sent_back_reason'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        sent_back_reason = cleaned_data.get('sent_back_reason')
        
        if action == 'rejected' and not rejection_reason:
            self.add_error('rejection_reason', 'Rejection reason is required.')
        
        if action == 'sent_back' and not sent_back_reason:
            self.add_error('sent_back_reason', 'Please provide comments explaining what needs to be revised.')
        
        # Set the actual status based on action
        if action == 'authorized':
            cleaned_data['status'] = 'authorized'
        elif action == 'sent_back':
            cleaned_data['status'] = 'sent_back'
        elif action == 'rejected':
            cleaned_data['status'] = 'rejected'
        
        return cleaned_data


class RequisitionFilterForm(forms.Form):
    """Form for filtering requisition lists"""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Requisition.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
