from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Department


class UserCreationForm(UserCreationForm):
    """
    Form for creating new users with department validation for initiators and HODs.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
        
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department')
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'department': 'Department',
        }
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        department = cleaned_data.get('department')

        # Require department for initiators and HODs
        if role in ['initiator', 'hod'] and not department:
            self.add_error('department', 'Department is required for Initiators and HODs.')
        
        return cleaned_data


class UserChangeForm(UserChangeForm):
    """
    Form for changing user information.
    """
    password = None  # Hide password field in change form

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_active')
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'department': 'Department',
            'is_active': 'Active',
        }
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SuperAdminUserCreationForm(UserCreationForm):
    """
    Form for super admin to create new users with all role options including other super admins.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
        for field_name in ['employee_id', 'phone', 'email']:
            self.fields[field_name].required = False
        
        # Apply consistent form-control styling to all fields
        for field_name, field in self.fields.items():
            if field_name in ['role', 'department']:
                field.widget.attrs['class'] = 'form-select'
            elif field_name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'employee_id', 'phone')
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'department': 'Department',
            'employee_id': 'Employee ID',
            'phone': 'Phone',
        }

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        department = cleaned_data.get('department')

        # Require department for initiators and HODs
        if role in ['initiator', 'hod'] and not department:
            self.add_error('department', 'Department is required for Initiators and HODs.')
        
        return cleaned_data


class DepartmentForm(forms.ModelForm):
    """
    Form for creating and updating departments.
    """
    class Meta:
        model = Department
        fields = ('name', 'code', 'is_active')
        labels = {
            'name': 'Department Name',
            'code': 'Department Code',
            'is_active': 'Active',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter department name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., HR, IT, FIN'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'employee_id', 'phone', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make certain fields optional
        for field_name in ['employee_id', 'phone', 'email']:
            self.fields[field_name].required = False