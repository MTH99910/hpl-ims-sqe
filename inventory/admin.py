"""
Inventory App - Admin Configuration
"""

from django.contrib import admin
from .models import Item, Location, Transaction


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('item', 'user', 'transaction_type', 'quantity_change', 
                       'balance_after', 'reference', 'notes', 'timestamp')
    can_delete = False
    max_num = 0


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('material_code', 'description', 'item_type', 'location', 
                    'quantity_total', 'reorder_level', 'is_active')
    list_filter = ('item_type', 'location', 'is_active')
    search_fields = ('material_code', 'description')
    ordering = ('item_type', 'material_code')
    inlines = [TransactionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('material_code', 'description', 'item_type', 'unit_of_measurement')
        }),
        ('Inventory Details', {
            'fields': ('location', 'quantity_total', 'reorder_level', 'is_active')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('location')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('item', 'user', 'transaction_type', 'quantity_change', 
                    'balance_after', 'reference', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('item__material_code', 'user__username', 'reference')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('item', 'user', 'item__location')
