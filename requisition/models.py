"""
Requisition App - Models for Requisition Workflow
"""

from django.db import models
from django.conf import settings
from django.utils.html import mark_safe
from django.urls import reverse
from inventory.models import Item


class Requisition(models.Model):
    """Requisition request for inventory items"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_hod', 'Pending HOD Approval'),
        ('sent_back', 'Sent Back for Revision'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled'),
    ]
    
    requisition_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated requisition number"
    )
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requisitions',
        help_text="User who created the requisition"
    )
    hod_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requisitions',
        help_text="HOD who approved the requisition"
    )
    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_requisitions',
        help_text="Admin who issued the items"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending_hod',
        help_text="Current status of the requisition"
    )
    purpose = models.TextField(
        help_text="Reason/purpose for the requisition"
    )
    department = models.CharField(
        max_length=100,
        help_text="Department of the initiator"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes from HOD or Admin"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection"
    )
    sent_back_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Comments/feedback when requisition was sent back for revision"
    )
    sent_back_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When requisition was sent back"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hod_action_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When HOD took action"
    )
    issued_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When items were issued"
    )
    
    class Meta:
        verbose_name = 'Requisition'
        verbose_name_plural = 'Requisitions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['initiator', 'status']),
            models.Index(fields=['requisition_number']),
        ]
    
    def __str__(self):
        return f"{self.requisition_number} - {self.initiator.get_full_name()} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse('requisition:detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Generate requisition number for new requisitions
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            count = Requisition.objects.filter(
                created_at__date=timezone.now().date()
            ).count() + 1
            self.requisition_number = f"REQ-{date_str}-{count:04d}"
            self.department = self.initiator.department.name if self.initiator.department else 'Unknown'
        super().save(*args, **kwargs)
    
    def get_status_badge(self):
        """Get Bootstrap badge class for status"""
        badges = {
            'draft': 'bg-secondary',
            'pending_hod': 'bg-warning text-dark',
            'sent_back': 'bg-info text-dark',
            'authorized': 'bg-primary',
            'rejected': 'bg-danger',
            'issued': 'bg-success',
            'cancelled': 'bg-dark',
        }
        return badges.get(self.status, 'bg-secondary')
    
    def get_status_icon(self):
        """Get icon for status"""
        icons = {
            'draft': 'bi-pencil',
            'pending_hod': 'bi-clock',
            'sent_back': 'bi-arrow-repeat',
            'authorized': 'bi-check-circle',
            'rejected': 'bi-x-circle',
            'issued': 'bi-box-seam',
            'cancelled': 'bi-slash-circle',
        }
        return icons.get(self.status, 'bi-question')
    
    def get_total_requested(self):
        """Get total quantity requested across all line items"""
        return sum(item.quantity_requested for item in self.items.all())
    
    def get_total_issued(self):
        """Get total quantity issued across all line items"""
        return sum(item.quantity_issued for item in self.items.all())
    
    def can_be_edited(self):
        """Check if requisition can be edited"""
        return self.status in ['draft', 'pending_hod', 'sent_back']
    
    def can_be_approved(self):
        """Check if requisition can be approved by HOD"""
        return self.status == 'pending_hod'
    
    def can_be_sent_back(self):
        """Check if requisition can be sent back by HOD"""
        return self.status == 'pending_hod'
    
    def can_be_resubmitted(self):
        """Check if requisition can be resubmitted by initiator"""
        return self.status == 'sent_back'
    
    def can_be_issued(self):
        """Check if requisition can be issued by Admin"""
        return self.status == 'authorized'
    
    def is_pending_action(self, user):
        """Check if there's a pending action for the user"""
        if user.is_hod and self.status == 'pending_hod':
            if user.department and self.initiator.department == user.department:
                return True
        elif user.is_admin and self.status == 'authorized':
            return True
        return False


class RequisitionLineItem(models.Model):
    """Individual items in a requisition"""
    
    requisition = models.ForeignKey(
        Requisition,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='requisition_items'
    )
    quantity_requested = models.IntegerField(
        help_text="Quantity requested by initiator"
    )
    quantity_issued = models.IntegerField(
        default=0,
        help_text="Quantity actually issued by Admin"
    )
    uom = models.CharField(
        max_length=20,
        help_text="Unit of measurement"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Specific notes for this item"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Line Item'
        verbose_name_plural = 'Line Items'
        ordering = ['requisition', 'item']
    
    def __str__(self):
        return f"{self.item.material_code} - {self.quantity_requested} {self.uom}"
    
    def get_status_display(self):
        """Get display status for this line item"""
        if self.quantity_issued == 0:
            return 'Pending'
        elif self.quantity_issued < self.quantity_requested:
            return f'Partial ({self.quantity_issued}/{self.quantity_requested})'
        else:
            return 'Fulfilled'
    
    def is_fully_issued(self):
        """Check if item is fully issued"""
        return self.quantity_issued >= self.quantity_requested
    
    def get_short_description(self):
        """Get shortened description for display"""
        if len(self.item.description) > 40:
            return self.item.description[:40] + '...'
        return self.item.description
