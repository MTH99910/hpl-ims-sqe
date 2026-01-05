"""
Core App - Models for User Management
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.html import mark_safe


class Department(models.Model):
    """Department model for organizing users and controlling HOD authorization scope"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    """Custom User model with role-based access control"""
    
    ROLE_CHOICES = [
        ('initiator', 'Initiator'),
        ('hod', 'Head of Department'),
        ('admin', 'Admin/Issuer'),
        ('super_admin', 'Super Admin'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='initiator',
        help_text="User role determines permissions and workflow capabilities"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Department for HOD authorization scope"
    )
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="HPL Employee ID"
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['department', 'username']

    def __str__(self):
        role_display = dict(self.ROLE_CHOICES).get(self.role, self.role)
        dept_name = self.department.name if self.department else 'No Department'
        return f"{self.get_full_name()} ({role_display} - {dept_name})"

    def get_full_name(self):
        """Returns the user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_super_admin(self):
        """Check if user is a Super Admin"""
        return self.role == 'super_admin'

    @property
    def is_hod(self):
        """Check if user is a Head of Department"""
        return self.role == 'hod'

    @property
    def is_admin(self):
        """Check if user is an Admin/Issuer"""
        return self.role == 'admin'

    @property
    def is_initiator(self):
        """Check if user is an Initiator"""
        return self.role == 'initiator'

    def get_pending_requisitions_count(self):
        """Get count of pending requisitions based on role"""
        if self.is_super_admin:
            from requisition.models import Requisition
            return Requisition.objects.filter(
                status__in=['pending_hod', 'authorized']
            ).count()
        elif self.is_hod:
            from requisition.models import Requisition
            return Requisition.objects.filter(
                status='pending_hod',
                initiator__department=self.department
            ).count()
        elif self.is_admin:
            from requisition.models import Requisition
            return Requisition.objects.filter(status='authorized').count()
        return 0

    def get_unread_notifications_count(self):
        """Get count of unread notifications"""
        return self.notifications.filter(is_read=False).count()


class Notification(models.Model):
    """Notification model for status change alerts"""
    
    NOTIFICATION_TYPES = [
        ('requisition_created', 'Requisition Created'),
        ('requisition_approved', 'Requisition Approved'),
        ('requisition_rejected', 'Requisition Rejected'),
        ('requisition_sent_back', 'Requisition Sent Back'),
        ('requisition_issued', 'Requisition Issued'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_icon(self):
        """Get Bootstrap icon based on notification type"""
        icons = {
            'requisition_created': 'bi-plus-circle text-primary',
            'requisition_approved': 'bi-check-circle text-success',
            'requisition_rejected': 'bi-x-circle text-danger',
            'requisition_sent_back': 'bi-arrow-repeat text-warning',
            'requisition_issued': 'bi-box-seam text-success',
        }
        return icons.get(self.notification_type, 'bi-bell')
