"""
Inventory App - Models for Item Management
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.html import mark_safe
from django.urls import reverse


class Location(models.Model):
    """Storage locations in the warehouse"""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['code']
    
    def __str__(self):
        return f"Location {self.code} - {self.name}"


class Item(models.Model):
    """Inventory items (Stationery and Housekeeping)"""
    
    ITEM_TYPE_CHOICES = [
        ('stationery', 'Stationery Item'),
        ('housekeeping', 'Housekeeping Item'),
    ]
    
    UOM_CHOICES = [
        ('pcs', 'Pieces (pcs)'),
        ('box', 'Box'),
        ('pack', 'Pack'),
        ('ream', 'Ream'),
        ('kg', 'Kilogram (kg)'),
        ('liter', 'Liter'),
        ('dozen', 'Dozen'),
        ('set', 'Set'),
        ('roll', 'Roll'),
        ('bottle', 'Bottle'),
    ]
    
    material_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique material code (e.g., ST001, HK001)"
    )
    description = models.TextField(
        help_text="Item description and details"
    )
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        help_text="Type of item"
    )
    unit_of_measurement = models.CharField(
        max_length=20,
        choices=UOM_CHOICES,
        default='pcs',
        help_text="Unit of measurement for this item"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        help_text="Storage location (Rack/Shelf 1-5)"
    )
    quantity_total = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total quantity currently in stock"
    )
    reorder_level = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text="Minimum quantity before reordering"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
        ordering = ['item_type', 'material_code']
        indexes = [
            models.Index(fields=['material_code']),
            models.Index(fields=['item_type']),
            models.Index(fields=['location']),
        ]
    
    def __str__(self):
        return f"{self.material_code} - {self.description[:50]}"
    
    def get_absolute_url(self):
        return reverse('inventory:detail', kwargs={'pk': self.pk})
    
    @property
    def is_low_stock(self):
        """Check if item is below reorder level"""
        return self.quantity_total <= self.reorder_level
    
    @property
    def stock_status(self):
        """Get stock status display"""
        if self.quantity_total == 0:
            return 'out_of_stock'
        elif self.quantity_total <= self.reorder_level:
            return 'low_stock'
        else:
            return 'in_stock'
    
    def get_stock_badge(self):
        """Get Bootstrap badge class for stock status"""
        status = self.stock_status
        if status == 'out_of_stock':
            return 'bg-danger'
        elif status == 'low_stock':
            return 'bg-warning'
        else:
            return 'bg-success'
    
    def get_stock_status_display(self):
        """Get human-readable stock status"""
        status = self.stock_status
        if status == 'out_of_stock':
            return 'Out of Stock'
        elif status == 'low_stock':
            return 'Low Stock'
        else:
            return 'In Stock'
    
    def get_type_badge(self):
        """Get Bootstrap badge class for item type"""
        if self.item_type == 'stationery':
            return 'bg-primary'
        else:
            return 'bg-info'
    
    def get_type_icon(self):
        """Get icon for item type"""
        if self.item_type == 'stationery':
            return 'bi-pencil-square'
        else:
            return 'bi-basket'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create initial stock transaction if new item with quantity > 0
        if is_new and self.quantity_total > 0:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # Try to get system user, or use first superuser, or None
            system_user = None
            try:
                system_user = User.objects.filter(is_superuser=True).first()
            except:
                pass
            
            Transaction.objects.create(
                item=self,
                user=system_user,
                transaction_type='inward',
                quantity_change=self.quantity_total,
                balance_after=self.quantity_total,
                reference=f"Initial stock for {self.material_code}",
                notes=f'Initial stock setup for {self.material_code}'
            )


class Transaction(models.Model):
    """Track all inventory movements datewise"""
    
    TRANSACTION_TYPES = [
        ('inward', 'Inward (Stock Received)'),
        ('outward', 'Outward (Issued)'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return to Stock'),
        ('write_off', 'Write Off'),
    ]
    
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='transactions',
        help_text="Item involved in transaction"
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions',
        help_text="User who performed the transaction"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    quantity_change = models.IntegerField(
        help_text="Positive for additions, negative for deductions"
    )
    balance_after = models.IntegerField(
        help_text="Stock balance after this transaction"
    )
    reference = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Reference (Requisition ID, PO number, etc.)"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for the transaction"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the transaction occurred"
    )
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['item', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        sign = '+' if self.quantity_change > 0 else ''
        return f"{self.item.material_code}: {sign}{self.quantity_change} ({self.transaction_type}) on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def get_transaction_icon(self):
        """Get icon for transaction type"""
        icons = {
            'inward': 'bi-box-arrow-in-down',
            'outward': 'bi-box-arrow-up',
            'adjustment': 'bi-gear',
            'return': 'bi-arrow-repeat',
            'write_off': 'bi-trash',
        }
        return icons.get(self.transaction_type, 'bi-question')
    
    def get_quantity_display(self):
        """Get formatted quantity change with sign"""
        if self.quantity_change > 0:
            return f"+{self.quantity_change}"
        return str(self.quantity_change)
