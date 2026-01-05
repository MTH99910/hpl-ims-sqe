"""
Inventory App - Views for Item Management
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from datetime import datetime

from .models import Item, Location, Transaction
from .forms import ItemForm, LocationForm, StockAdjustmentForm, ItemSearchForm


class InventoryMixin(LoginRequiredMixin):
    """Mixin for inventory views with common functionality"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inventory Management'
        context['item_types'] = Item.ITEM_TYPE_CHOICES
        context['locations'] = Location.objects.filter(is_active=True)
        return context


class ItemListView(InventoryMixin, ListView):
    """List all inventory items with search and filter"""
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Item.objects.select_related('location').filter(is_active=True)
        
        # Search functionality
        search_type = self.request.GET.get('search_type')
        query = self.request.GET.get('query')
        if search_type and query:
            if search_type == 'code':
                queryset = queryset.filter(material_code__icontains=query)
            elif search_type == 'description':
                queryset = queryset.filter(description__icontains=query)
            elif search_type == 'type':
                queryset = queryset.filter(item_type=query)
        
        # Filter by type
        item_type = self.request.GET.get('type')
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        # Filter by location
        location = self.request.GET.get('location')
        if location:
            queryset = queryset.filter(location_id=location)
        
        # Filter low stock
        low_stock = self.request.GET.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(quantity_total__lte=models.F('reorder_level'))
        
        return queryset.order_by('item_type', 'material_code')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ItemSearchForm(self.request.GET)
        context['total_value'] = sum(item.quantity_total for item in context['items'])
        return context


class ItemDetailView(InventoryMixin, DetailView):
    """View item details with transaction history"""
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.object.transactions.select_related(
            'user'
        ).order_by('-timestamp')[:50]
        return context


class ItemCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new inventory item"""
    model = Item
    form_class = ItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('inventory:list')
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Item'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f"Item '{form.instance.material_code}' created successfully!")
        return super().form_valid(form)


class ItemUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update existing inventory item"""
    model = Item
    form_class = ItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('inventory:list')
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Item'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Item updated successfully!')
        return super().form_valid(form)


class StockAdjustmentView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """View for adjusting stock quantities"""
    template_name = 'inventory/stock_adjustment.html'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stock Adjustment'
        context['item'] = get_object_or_404(Item, pk=kwargs.get('pk'))
        return context
    
    def post(self, request, *args, **kwargs):
        item = get_object_or_404(Item, pk=kwargs.get('pk'))
        form = StockAdjustmentForm(request.POST, item=item, initial={
            'user': request.user,
            'reference': f"Stock adjustment by {request.user.get_full_name()}"
        })
        
        if form.is_valid():
            form.save()
            messages.success(request, f"Stock adjusted for {item.material_code}")
            return redirect('inventory:detail', pk=item.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return self.render_to_response({
            'title': 'Stock Adjustment',
            'item': item,
            'form': form
        })


class TransactionListView(InventoryMixin, ListView):
    """List all transactions with filters"""
    model = Transaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Transaction.objects.select_related(
            'item', 'item__location', 'user', 'user__department'
        ).all()
        
        # Filter by item
        item_id = self.request.GET.get('item')
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        # Filter by transaction type
        txn_type = self.request.GET.get('type')
        if txn_type:
            queryset = queryset.filter(transaction_type=txn_type)
        
        # Filter by user
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        return queryset.order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = Item.objects.filter(is_active=True)
        context['transaction_types'] = Transaction.TRANSACTION_TYPES
        return context


class LocationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all locations"""
    model = Location
    template_name = 'inventory/location_list.html'
    context_object_name = 'locations'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Location Management'
        return context


class LocationCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new location"""
    model = Location
    form_class = LocationForm
    template_name = 'inventory/location_form.html'
    success_url = reverse_lazy('inventory:location_list')
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Location'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Location created successfully!')
        return super().form_valid(form)


class LocationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update existing location"""
    model = Location
    form_class = LocationForm
    template_name = 'inventory/location_form.html'
    success_url = reverse_lazy('inventory:location_list')
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Location'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Location updated successfully!')
        return super().form_valid(form)


@login_required
def item_delete_view(request, pk):
    """Soft delete an item (Admin only)"""
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, 'You do not have permission to delete items.')
        return redirect('inventory:list')
    
    item = get_object_or_404(Item, pk=pk)
    item.is_active = False
    item.save()
    messages.success(request, f"Item '{item.material_code}' has been deactivated.")
    return redirect('inventory:list')


@login_required
def get_item_details(request):
    """API endpoint to get item details for autocomplete"""
    query = request.GET.get('q', '')
    item_type = request.GET.get('type', '')
    
    items = Item.objects.filter(
        is_active=True,
        material_code__icontains=query
    )[:10]
    
    if item_type:
        items = items.filter(item_type=item_type)
    
    data = [{
        'id': item.pk,
        'material_code': item.material_code,
        'description': item.description,
        'item_type': item.item_type,
        'uom': item.unit_of_measurement,
        'quantity_total': item.quantity_total,
        'location': item.location.code if item.location else 'N/A'
    } for item in items]
    
    return JsonResponse(data, safe=False)
