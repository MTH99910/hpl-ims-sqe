"""
Requisition App - Admin Configuration
"""

from django.contrib import admin
from .models import Requisition, RequisitionLineItem


class RequisitionLineItemInline(admin.TabularInline):
    model = RequisitionLineItem
    extra = 0
    readonly_fields = ('item', 'quantity_requested', 'uom', 'quantity_issued', 'created_at')
    can_delete = False
    max_num = 0


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = ('requisition_number', 'initiator', 'department', 'status', 
                    'created_at', 'hod_action_date', 'issued_date')
    list_filter = ('status', 'department', 'created_at')
    search_fields = ('requisition_number', 'initiator__username', 
                     'initiator__first_name', 'purpose')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    inlines = [RequisitionLineItemInline]
    
    fieldsets = (
        ('Request Details', {
            'fields': ('requisition_number', 'initiator', 'department', 'purpose')
        }),
        ('Approval', {
            'fields': ('status', 'hod_approver', 'hod_action_date', 'notes')
        }),
        ('Issuance', {
            'fields': ('issuer', 'issued_date', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('requisition_number', 'initiator', 'department',
                       'created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'initiator', 'initiator__department',
            'hod_approver', 'issuer'
        )


@admin.register(RequisitionLineItem)
class RequisitionLineItemAdmin(admin.ModelAdmin):
    list_display = ('requisition', 'item', 'quantity_requested', 
                    'quantity_issued', 'uom')
    list_filter = ('item__item_type', 'uom')
    search_fields = ('requisition__requisition_number', 'item__material_code')
    ordering = ('requisition', 'item')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('requisition', 'item')
