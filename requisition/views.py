"""
Requisition App - Views for Requisition Workflow
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, models
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.forms import formset_factory,inlineformset_factory
import json

from .models import Requisition, RequisitionLineItem
from .forms import (
    RequisitionCreateForm, RequisitionLineItemForm, 
    RequisitionLineItemUpdateForm, HODActionForm,
    RequisitionFilterForm
)
from inventory.models import Item, Transaction
from core.models import Notification, User


def create_requisition_notification(requisition, notification_type, recipient_user):
    """Helper to create notifications for requisition status changes"""
    titles = {
        'requisition_created': f'New Requisition: {requisition.requisition_number}',
        'requisition_approved': f'Requisition Approved: {requisition.requisition_number}',
        'requisition_rejected': f'Requisition Rejected: {requisition.requisition_number}',
        'requisition_sent_back': f'Requisition Sent Back: {requisition.requisition_number}',
        'requisition_issued': f'Items Issued: {requisition.requisition_number}',
    }
    
    messages_map = {
        'requisition_created': f'A new requisition has been submitted by {requisition.initiator.get_full_name()} and requires your approval.',
        'requisition_approved': f'Your requisition has been approved by {requisition.hod_approver.get_full_name() if requisition.hod_approver else "HOD"}.',
        'requisition_rejected': f'Your requisition has been rejected. Reason: {requisition.rejection_reason or "Not specified"}',
        'requisition_sent_back': f'Your requisition has been sent back for revision. Comments: {requisition.sent_back_reason or "Please review"}',
        'requisition_issued': f'Items for your requisition have been issued by {requisition.issuer.get_full_name() if requisition.issuer else "Admin"}.',
    }
    
    Notification.objects.create(
        user=recipient_user,
        notification_type=notification_type,
        title=titles.get(notification_type, 'Requisition Update'),
        message=messages_map.get(notification_type, 'There is an update to a requisition.'),
        link=reverse('requisition:detail', kwargs={'pk': requisition.pk})
    )


class RequisitionMixin(LoginRequiredMixin):
    """Mixin for requisition views with common functionality"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Requisition Management'
        context['STATUS_CHOICES'] = Requisition.STATUS_CHOICES
        return context


class InitiatorRequiredMixin(UserPassesTestMixin):
    """Mixin to require initiator access"""
    def test_func(self):
        return self.request.user.role in ['initiator', 'hod', 'admin']


class HODRequiredMixin(UserPassesTestMixin):
    """Mixin to require HOD access"""
    def test_func(self):
        return self.request.user.is_hod or self.request.user.is_admin


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require Admin access"""
    def test_func(self):
        return self.request.user.is_admin


class InitiatorDashboardView(RequisitionMixin, TemplateView):
    """Dashboard for Initiators"""
    template_name = 'requisition/initiator_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['my_requisitions'] = Requisition.objects.filter(
            initiator=user
        ).select_related('hod_approver', 'issuer').order_by('-created_at')[:10]
        
        context['pending_count'] = Requisition.objects.filter(
            initiator=user,
            status__in=['pending_hod', 'authorized']
        ).count()
        
        context['completed_count'] = Requisition.objects.filter(
            initiator=user,
            status='issued'
        ).count()
        
        # Get sent back requisitions that need revision
        context['sent_back_requisitions'] = Requisition.objects.filter(
            initiator=user,
            status='sent_back'
        ).select_related('hod_approver').order_by('-updated_at')
        
        context['sent_back_count'] = context['sent_back_requisitions'].count()
        
        return context


class HODDashboardView(RequisitionMixin, TemplateView):
    """Dashboard for HOD with department-based approval queue"""
    template_name = 'requisition/hod_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.department:
            context['pending_approvals'] = Requisition.objects.filter(
                status='pending_hod',
                initiator__department=user.department
            ).select_related('initiator').order_by('-created_at')
            
            context['approval_count'] = context['pending_approvals'].count()
            
            context['recent_approvals'] = Requisition.objects.filter(
                hod_approver=user
            ).select_related('initiator').order_by('-hod_action_date')[:10]
        else:
            context['pending_approvals'] = []
            context['approval_count'] = 0
            context['recent_approvals'] = []
        
        return context


class AdminDashboardView(RequisitionMixin, TemplateView):
    """Dashboard for Admin with all pending issues"""
    template_name = 'requisition/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['pending_issues'] = Requisition.objects.filter(
            status='authorized'
        ).select_related('initiator', 'hod_approver').order_by('-created_at')
        
        context['pending_count'] = context['pending_issues'].count()
        
        context['recent_issues'] = Requisition.objects.filter(
            status='issued'
        ).select_related('initiator', 'hod_approver', 'issuer').order_by('-issued_date')[:10]
        
        context['total_requisitions'] = Requisition.objects.count()
        context['today_requisitions'] = Requisition.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        return context


class RequisitionListView(RequisitionMixin, ListView):
    """List requisitions with filters"""
    model = Requisition
    template_name = 'requisition/requisition_list.html'
    context_object_name = 'requisitions'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        queryset = Requisition.objects.select_related(
            'initiator', 'initiator__department',
            'hod_approver', 'issuer'
        ).all()
        
        # Role-based filtering
        if user.is_hod and user.department:
            queryset = queryset.filter(initiator__department=user.department)
        elif user.is_initiator:
            queryset = queryset.filter(initiator=user)
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = RequisitionFilterForm(self.request.GET)
        return context


class RequisitionDetailView(RequisitionMixin, DetailView):
    """View requisition details"""
    model = Requisition
    template_name = 'requisition/requisition_detail.html'
    context_object_name = 'requisition'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Role-based access
        if user.is_initiator:
            queryset = queryset.filter(initiator=user)
        elif user.is_hod and user.department:
            queryset = queryset.filter(initiator__department=user.department)
        
        return queryset.prefetch_related('items', 'items__item')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['line_items'] = self.object.items.select_related('item').all()
        return context


class RequisitionPrintView(RequisitionMixin, DetailView):
    """Printable view of requisition"""
    model = Requisition
    template_name = 'requisition/requisition_print.html'
    context_object_name = 'requisition'
    
    def get_queryset(self):
        return Requisition.objects.prefetch_related('items', 'items__item')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['line_items'] = self.object.items.select_related('item').all()
        return context


class RequisitionCreateView(RequisitionMixin, CreateView):
    """Create new requisition with line items"""
    model = Requisition
    form_class = RequisitionCreateForm
    template_name = 'requisition/requisition_form.html'
    
    def get_success_url(self):
        return reverse_lazy('requisition:initiator_dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Requisition'
        
        if 'line_items_formset' not in context:
            LineItemFormSet = formset_factory(
                RequisitionLineItemForm,
                extra=0,
                can_delete=True
            )
            context['line_items_formset'] = LineItemFormSet(
                prefix='items'
            )
        
        return context
    
    def form_valid(self, form):
        # Get POST data
        LineItemFormSet = formset_factory(
            RequisitionLineItemForm,
            extra=0,
            can_delete=True
        )
        line_items_formset = LineItemFormSet(
            self.request.POST,
            prefix='items'
        )
        
        # Debug: Print formset errors
        print("=== Formset Debug ===")
        print("Formset is_valid:", line_items_formset.is_valid())
        if not line_items_formset.is_valid():
            print("Formset errors:", line_items_formset.errors)
            print("Formset non_form_errors:", line_items_formset.non_form_errors())
            for i, form in enumerate(line_items_formset):
                print(f"Form {i} errors:", form.errors)
                print(f"Form {i} non_field_errors:", form.non_field_errors())
        
        # Check if formset is valid
        if not line_items_formset.is_valid():
            error_messages = []
            for error_list in line_items_formset.errors:
                for field, errors in error_list.items():
                    if errors:
                        error_messages.append(f"{field}: {', '.join(errors)}")
            for error in line_items_formset.non_form_errors():
                error_messages.append(str(error))
            
            error_msg = 'Please correct the errors in the items form: ' + '; '.join(error_messages)
            messages.error(self.request, error_msg)
            return self.render_to_response(self.get_context_data(form=form))
        
        # Get cleaned_data after validation
        items_data = line_items_formset.cleaned_data
        valid_items = [item for item in items_data if item and not item.get('DELETE', False)]
        
        if not valid_items:
            messages.error(self.request, 'Please add at least one item to the requisition.')
            return self.render_to_response(self.get_context_data(form=form))
        
        # Save requisition
        self.object = form.save(commit=False)
        self.object.initiator = self.request.user
        self.object.status = 'pending_hod'  # Ensure status is set
        self.object.save()
        
        # Save line items
        for item_data in valid_items:
            if item_data.get('item'):
                RequisitionLineItem.objects.create(
                    requisition=self.object,
                    item=item_data['item'],
                    quantity_requested=item_data['quantity_requested'],
                    uom=item_data['uom'],
                    notes=item_data.get('notes', '')
                )
        
        messages.success(self.request, f'Requisition {self.object.requisition_number} created successfully! Your request has been sent to HOD for approval.')
        return redirect(self.get_success_url())


class RequisitionUpdateView(RequisitionMixin, UpdateView):
    """Update requisition (for draft/pending/sent_back status)"""
    model = Requisition
    form_class = RequisitionCreateForm
    template_name = 'requisition/requisition_form.html'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(initiator=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('requisition:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if this is a resubmission of sent back requisition
        is_resubmission = self.object.status == 'sent_back'
        
        if is_resubmission:
            context['title'] = 'Resubmit Requisition'
            context['is_resubmission'] = True
            context['sent_back_reason'] = self.object.sent_back_reason
        else:
            context['title'] = 'Update Requisition'
            context['is_resubmission'] = False
        
        LineItemFormSet = formset_factory(
            RequisitionLineItemForm,
            extra=0,
            can_delete=True
        )
        
        initial_data = []
        existing_items_data = []  # For JavaScript
        for line_item in self.object.items.select_related('item').all():
            initial_data.append({
                'item': line_item.item,
                'quantity_requested': line_item.quantity_requested,
                'uom': line_item.uom,
                'notes': line_item.notes
            })
            # Detailed data for JavaScript
            existing_items_data.append({
                'id': line_item.item.pk,
                'material_code': line_item.item.material_code,
                'description': line_item.item.description,
                'quantity_requested': line_item.quantity_requested,
                'uom': line_item.uom,
                'notes': line_item.notes or ''
            })
        
        context['existing_items_json'] = json.dumps(existing_items_data)
        
        if initial_data:
            context['line_items_formset'] = LineItemFormSet(
                prefix='items',
                initial=initial_data
            )
        else:
            context['line_items_formset'] = LineItemFormSet(
                prefix='items',
                extra=1
            )
        
        return context
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        line_items_formset = context['line_items_formset']
        
        items_data = line_items_formset.cleaned_data
        valid_items = [item for item in items_data if item and not item.get('DELETE', False)]
        
        if not valid_items:
            messages.error(self.request, 'Please add at least one item to the requisition.')
            return self.render_to_response(self.get_context_data(form=form))
        
        # Save requisition
        self.object = form.save()
        
        # Check if this is a resubmission of sent back requisition
        is_resubmission = context.get('is_resubmission', False)
        
        # Delete removed items
        existing_ids = set(self.object.items.values_list('id', flat=True))
        new_ids = set()
        
        for item_data in valid_items:
            if item_data.get('DELETE', False):
                if item_data.get('item') and item_data['item'].pk:
                    RequisitionLineItem.objects.filter(
                        requisition=self.object,
                        item=item_data['item']
                    ).delete()
            else:
                if item_data.get('item'):
                    line_item, created = RequisitionLineItem.objects.update_or_create(
                        requisition=self.object,
                        item=item_data['item'],
                        defaults={
                            'quantity_requested': item_data['quantity_requested'],
                            'uom': item_data['uom'],
                            'notes': item_data.get('notes', '')
                        }
                    )
                    new_ids.add(line_item.id)
        
        # If resubmitting, change status back to pending_hod and clear send back fields
        if is_resubmission:
            self.object.status = 'pending_hod'
            self.object.sent_back_reason = None
            self.object.sent_back_at = None
            self.object.hod_approver = None
            self.object.hod_action_date = None
            self.object.save()
            messages.success(self.request, f'Requisition {self.object.requisition_number} has been resubmitted for HOD approval.')
        else:
            messages.success(self.request, 'Requisition updated successfully!')
        
        return redirect(self.get_success_url())


class HODApprovalView(RequisitionMixin, UpdateView):
    """HOD approval/rejection/send back of requisitions"""
    model = Requisition
    form_class = HODActionForm
    template_name = 'requisition/hod_approval.html'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_admin:
            return queryset
        elif user.is_hod and user.department:
            return queryset.filter(
                status='pending_hod',
                initiator__department=user.department
            )
        
        return queryset.none()
    
    def get_success_url(self):
        return reverse_lazy('requisition:hod_dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'HOD Approval'
        context['line_items'] = self.object.items.select_related('item').all()
        return context
    
    def form_valid(self, form):
        from django.utils import timezone
        
        self.object = form.save(commit=False)
        self.object.hod_approver = self.request.user
        self.object.hod_action_date = timezone.now()
        
        # Set sent_back_at if sending back
        if self.object.status == 'sent_back':
            self.object.sent_back_at = timezone.now()
        
        if self.object.status == 'authorized':
            messages.success(self.request, f'Requisition {self.object.requisition_number} has been approved.')
            # Notify initiator
            create_requisition_notification(self.object, 'requisition_approved', self.object.initiator)
            # Notify admins
            admins = User.objects.filter(role='admin')
            for admin in admins:
                create_requisition_notification(self.object, 'requisition_approved', admin)
        elif self.object.status == 'sent_back':
            messages.info(self.request, f'Requisition {self.object.requisition_number} has been sent back for revision.')
            # Notify initiator
            create_requisition_notification(self.object, 'requisition_sent_back', self.object.initiator)
        else:
            messages.warning(self.request, f'Requisition {self.object.requisition_number} has been rejected.')
            # Notify initiator
            create_requisition_notification(self.object, 'requisition_rejected', self.object.initiator)
        
        self.object.save()
        return redirect(self.get_success_url())


class IssueItemsView(RequisitionMixin, UpdateView):
    """Admin issuing items with quantity modification"""
    model = Requisition
    form_class = RequisitionCreateForm
    template_name = 'requisition/issue_items.html'
    
    def get_queryset(self):
        return Requisition.objects.filter(status='authorized')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Issue Items'
        
        # Create formset for updating quantities
        LineItemUpdateFormSet = inlineformset_factory(
            Requisition,
            RequisitionLineItem,
            form=RequisitionLineItemUpdateForm,
            extra=0,
            can_delete=False
        )
        
        if 'formset' not in context:
            context['formset'] = LineItemUpdateFormSet(
                instance=self.object,
                prefix='items'
            )
        
        context['line_items'] = self.object.items.select_related('item').all()
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        LineItemUpdateFormSet = inlineformset_factory(
            Requisition,
            RequisitionLineItem,
            form=RequisitionLineItemUpdateForm,
            extra=0,
            can_delete=False
        )
        
        formset = LineItemUpdateFormSet(
            request.POST,
            instance=self.object,
            prefix='items'
        )
        
        if formset.is_valid():
            return self.form_valid(formset)
        else:
            # Collect all errors
            error_messages = []
            for i, form in enumerate(formset):
                for field, errors in form.errors.items():
                    if errors:
                        error_messages.append(f"{field}: {', '.join(errors)}")
            
            if error_messages:
                messages.error(request, 'Please correct the errors: ' + '; '.join(error_messages))
            else:
                messages.error(request, 'Please correct the errors below.')
            return self.render_to_response(self.get_context_data(formset=formset))
    
    def form_valid(self, formset):
        requisition = self.object  # Get the requisition before saving formset
        
        with transaction.atomic():
            formset.save()  # This saves the line items
            
            # Refresh from database to get updated values
            requisition.refresh_from_db()
            
            # Process each line item from the formset's saved instances
            for line_item in requisition.items.all():
                item = line_item.item
                qty_issued = line_item.quantity_issued
                qty_requested = line_item.quantity_requested
                
                if qty_issued > 0:
                    # Create transaction record
                    Transaction.objects.create(
                        item=item,
                        user=self.request.user,
                        transaction_type='outward',
                        quantity_change=-qty_issued,
                        balance_after=item.quantity_total - qty_issued,
                        reference=requisition.requisition_number,
                        notes=f"Issued via requisition {requisition.requisition_number}"
                    )
                    
                    # Update item quantity
                    item.quantity_total -= qty_issued
                    item.save()
            
            # Update requisition status
            requisition.issuer = self.request.user
            requisition.status = 'issued'
            requisition.issued_date = timezone.now()
            requisition.save()
            
            # Notify initiator that items have been issued
            create_requisition_notification(requisition, 'requisition_issued', requisition.initiator)
        
        messages.success(self.request, f'Items issued for requisition {requisition.requisition_number}')
        return redirect('requisition:admin_dashboard')


@login_required
def cancel_requisition(request, pk):
    """Cancel a requisition (initiator only, if pending)"""
    requisition = get_object_or_404(
        Requisition.objects.filter(initiator=request.user),
        pk=pk
    )
    
    if requisition.status not in ['draft', 'pending_hod']:
        messages.error(request, 'Cannot cancel this requisition.')
        return redirect('requisition:detail', pk=pk)
    
    requisition.status = 'cancelled'
    requisition.save()
    messages.success(request, f'Requisition {requisition.requisition_number} has been cancelled.')
    return redirect('requisition:list')


@login_required
def get_item_suggestions(request):
    """API endpoint for item autocomplete and search"""
    query = request.GET.get('q', '').strip()
    item_type = request.GET.get('type', '')
    
    # Base queryset - only show active items
    items = Item.objects.filter(is_active=True)
    
    # Search by both material code and description
    if query:
        items = items.filter(
            models.Q(material_code__icontains=query) |
            models.Q(description__icontains=query)
        )
    
    # Filter by item type if specified
    if item_type:
        items = items.filter(item_type=item_type)
    
    # Order by material code and limit results
    items = items.order_by('material_code')[:20]
    
    # Build response data
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


@login_required
def create_requisition_api(request):
    """API endpoint for creating requisitions via AJAX"""
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        print("=== API Requisition Creation ===")
        print("Received data:", json.dumps(data, indent=2))
        
        purpose = data.get('purpose', '').strip()
        notes = data.get('notes', '').strip()
        items = data.get('items', [])
        
        # Validation
        if not purpose:
            return JsonResponse({'success': False, 'error': 'Purpose is required'}, status=400)
        
        if len(purpose) < 10:
            return JsonResponse({'success': False, 'error': 'Purpose must be at least 10 characters'}, status=400)
        
        if not items or len(items) == 0:
            return JsonResponse({'success': False, 'error': 'At least one item is required'}, status=400)
        
        # Validate each item
        for i, item in enumerate(items):
            item_id = item.get('id')
            qty = item.get('qty', 0)
            
            if not item_id:
                return JsonResponse({'success': False, 'error': f'Item {i+1}: Item ID is required'}, status=400)
            
            if qty < 1:
                return JsonResponse({'success': False, 'error': f'Item {i+1}: Quantity must be at least 1'}, status=400)
        
        # Create requisition
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        count = Requisition.objects.filter(
            created_at__date=timezone.now().date()
        ).count() + 1
        requisition_number = f"REQ-{date_str}-{count:04d}"
        
        # Get department from user
        department = request.user.department.name if request.user.department else 'Unknown'
        
        requisition = Requisition.objects.create(
            requisition_number=requisition_number,
            initiator=request.user,
            purpose=purpose,
            notes=notes,
            department=department,
            status='pending_hod'
        )
        
        # Create line items
        for item_data in items:
            item = Item.objects.get(pk=item_data['id'])
            RequisitionLineItem.objects.create(
                requisition=requisition,
                item=item,
                quantity_requested=item_data['qty'],
                uom=item_data.get('uom', 'pcs'),
                notes=item_data.get('notes', '')
            )
        
        # Notify HODs in the same department
        if request.user.department:
            hods = User.objects.filter(role='hod', department=request.user.department)
            for hod in hods:
                create_requisition_notification(requisition, 'requisition_created', hod)
        
        print(f"Created requisition: {requisition_number}")
        
        return JsonResponse({
            'success': True,
            'message': f'Requisition {requisition_number} created successfully!',
            'requisition_id': requisition.pk,
            'requisition_number': requisition_number
        })
        
    except json.JSONDecodeError as e:
        print("JSON decode error:", str(e))
        return JsonResponse({'success': False, 'error': f'Invalid JSON: {str(e)}'}, status=400)
    
    except Exception as e:
        print("Error creating requisition:", str(e))
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required
def update_requisition_api(request, pk):
    """API endpoint for updating/resubmitting requisitions via AJAX"""
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)
    
    try:
        requisition = get_object_or_404(Requisition, pk=pk, initiator=request.user)
        
        # Check if requisition can be updated
        if requisition.status not in ['draft', 'pending_hod', 'sent_back']:
            return JsonResponse({'success': False, 'error': 'This requisition cannot be modified'}, status=400)
        
        data = json.loads(request.body)
        
        purpose = data.get('purpose', '').strip()
        notes = data.get('notes', '').strip()
        items = data.get('items', [])
        
        # Validation
        if not purpose:
            return JsonResponse({'success': False, 'error': 'Purpose is required'}, status=400)
        
        if len(purpose) < 10:
            return JsonResponse({'success': False, 'error': 'Purpose must be at least 10 characters'}, status=400)
        
        if not items or len(items) == 0:
            return JsonResponse({'success': False, 'error': 'At least one item is required'}, status=400)
        
        # Validate each item
        for i, item in enumerate(items):
            item_id = item.get('id')
            qty = item.get('qty', 0)
            
            if not item_id:
                return JsonResponse({'success': False, 'error': f'Item {i+1}: Item ID is required'}, status=400)
            
            if qty < 1:
                return JsonResponse({'success': False, 'error': f'Item {i+1}: Quantity must be at least 1'}, status=400)
        
        # Check if this is a resubmission
        is_resubmission = requisition.status == 'sent_back'
        
        # Update requisition
        requisition.purpose = purpose
        requisition.notes = notes
        
        if is_resubmission:
            requisition.status = 'pending_hod'
            requisition.sent_back_reason = None
            requisition.sent_back_at = None
            requisition.hod_approver = None
            requisition.hod_action_date = None
        
        requisition.save()
        
        # Delete existing line items and create new ones
        requisition.items.all().delete()
        
        for item_data in items:
            item = Item.objects.get(pk=item_data['id'])
            RequisitionLineItem.objects.create(
                requisition=requisition,
                item=item,
                quantity_requested=item_data['qty'],
                uom=item_data.get('uom', 'pcs'),
                notes=item_data.get('notes', '')
            )
        
        if is_resubmission:
            message = f'Requisition {requisition.requisition_number} has been resubmitted for HOD approval.'
            # Notify HODs in the same department
            if request.user.department:
                hods = User.objects.filter(role='hod', department=request.user.department)
                for hod in hods:
                    create_requisition_notification(requisition, 'requisition_created', hod)
        else:
            message = f'Requisition {requisition.requisition_number} updated successfully!'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'requisition_id': requisition.pk,
            'requisition_number': requisition.requisition_number
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Invalid JSON: {str(e)}'}, status=400)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)
