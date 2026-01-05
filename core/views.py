"""
Core App - Views for Authentication and Dashboard
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, UpdateView, TemplateView, CreateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import models
from django.db.models import Count, Q, F
from datetime import datetime, timedelta

from .models import User, Department, Notification
from .forms import UserCreationForm, UserUpdateForm, DepartmentForm, SuperAdminUserCreationForm
from inventory.models import Item, Transaction
from requisition.models import Requisition


class LoginView(TemplateView):
    """Custom login view with role-based redirect"""
    template_name = 'core/login.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login - HPL Inventory Management System'
        return context


def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            
            # Role-based redirect
            if user.is_super_admin:
                return redirect('core:super_admin_dashboard')
            elif user.is_admin:
                return redirect('requisition:admin_dashboard')
            elif user.is_hod:
                return redirect('requisition:hod_dashboard')
            else:
                return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'core/login.html', {'title': 'Login'})


@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('core:login')


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for all users"""
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['title'] = 'Dashboard'
        
        if user.is_admin:
            # Admin Dashboard
            context['total_items'] = Item.objects.count()
            context['total_requisitions'] = Requisition.objects.count()
            context['pending_requisitions'] = Requisition.objects.filter(
                status__in=['pending_hod', 'authorized']
            ).count()
            context['today_requisitions'] = Requisition.objects.filter(
                created_at__date=datetime.now().date()
            ).count()
            
            # Recent transactions
            context['recent_transactions'] = Transaction.objects.select_related(
                'item', 'user'
            ).order_by('-timestamp')[:10]
            
        elif user.is_super_admin:
            # Super Admin Dashboard
            context['total_users'] = User.objects.count()
            context['total_items'] = Item.objects.count()
            context['total_requisitions'] = Requisition.objects.count()
            context['pending_hod'] = Requisition.objects.filter(status='pending_hod').count()
            context['authorized'] = Requisition.objects.filter(status='authorized').count()
            context['issued'] = Requisition.objects.filter(status='issued').count()
            context['recent_requisitions'] = Requisition.objects.select_related(
                'initiator', 'initiator__department', 'hod_approver'
            ).order_by('-created_at')[:10]
            context['recent_transactions'] = Transaction.objects.select_related(
                'item', 'user'
            ).order_by('-timestamp')[:10]
            
        elif user.is_hod:
            # HOD Dashboard
            if user.department:
                context['pending_approvals'] = Requisition.objects.filter(
                    status='pending_hod',
                    initiator__department=user.department
                ).count()
                context['dept_requests'] = Requisition.objects.filter(
                    initiator__department=user.department
                ).count()
                context['recent_requests'] = Requisition.objects.filter(
                    initiator__department=user.department
                ).select_related('initiator').order_by('-created_at')[:10]
            else:
                context['pending_approvals'] = 0
                context['dept_requests'] = 0
                context['recent_requests'] = []
                
        else:
            # Initiator Dashboard
            context['my_requisitions'] = Requisition.objects.filter(
                initiator=user
            ).count()
            context['pending_requisitions'] = Requisition.objects.filter(
                initiator=user,
                status__in=['pending_hod', 'authorized']
            ).count()
            context['recent_requisitions'] = Requisition.objects.filter(
                initiator=user
            ).select_related('hod_approver', 'issuer').order_by('-created_at')[:10]
        
        return context


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_super_admin or self.request.user.is_superuser


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require super admin access"""
    def test_func(self):
        return self.request.user.is_super_admin or self.request.user.is_superuser


class HODRequiredMixin(UserPassesTestMixin):
    """Mixin to require HOD access"""
    def test_func(self):
        return self.request.user.is_hod


class UserListView(AdminRequiredMixin, ListView):
    """List all users - Admin only"""
    model = User
    template_name = 'core/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.select_related('department').all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'User Management'
        context['departments'] = Department.objects.filter(is_active=True)
        return context


class UserCreateView(AdminRequiredMixin, UpdateView):
    """Create new user - Admin only"""
    model = User
    form_class = UserCreationForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create User'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)


class UserUpdateView(AdminRequiredMixin, UpdateView):
    """Update existing user - Admin only"""
    model = User
    form_class = UserUpdateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update User'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)


class DepartmentListView(AdminRequiredMixin, ListView):
    """List all departments - Admin only"""
    model = Department
    template_name = 'core/department_list.html'
    context_object_name = 'departments'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Department Management'
        return context


class DepartmentCreateView(AdminRequiredMixin, CreateView):
    """Create departments - Admin only"""
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Department'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Department saved successfully!')
        return super().form_valid(form)


# Super Admin Views

class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    """Super Admin Dashboard with overview of everything"""
    template_name = 'core/super_admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Super Admin Dashboard'
        
        # User statistics
        context['total_users'] = User.objects.count()
        context['super_admins'] = User.objects.filter(role='super_admin').count()
        context['admins'] = User.objects.filter(role='admin').count()
        context['hods'] = User.objects.filter(role='hod').count()
        context['initiators'] = User.objects.filter(role='initiator').count()
        
        # Item statistics
        context['total_items'] = Item.objects.count()
        context['active_items'] = Item.objects.filter(is_active=True).count()
        context['low_stock_items'] = Item.objects.filter(
            is_active=True
        ).filter(models.Q(quantity_total__lte=models.F('reorder_level'))).count()
        
        # Requisition statistics
        context['total_requisitions'] = Requisition.objects.count()
        context['pending_hod'] = Requisition.objects.filter(status='pending_hod').count()
        context['authorized'] = Requisition.objects.filter(status='authorized').count()
        context['issued'] = Requisition.objects.filter(status='issued').count()
        context['rejected'] = Requisition.objects.filter(status='rejected').count()
        context['cancelled'] = Requisition.objects.filter(status='cancelled').count()
        
        # Recent activity
        context['recent_requisitions'] = Requisition.objects.select_related(
            'initiator', 'initiator__department', 'hod_approver'
        ).order_by('-created_at')[:10]
        context['recent_transactions'] = Transaction.objects.select_related(
            'item', 'user'
        ).order_by('-timestamp')[:10]
        
        # Department overview
        context['departments'] = Department.objects.annotate(
            user_count=Count('users'),
            requisition_count=Count('users__requisitions')
        ).order_by('name')
        
        return context


class UserManagementView(SuperAdminRequiredMixin, ListView):
    """User Management for Super Admin"""
    model = User
    template_name = 'core/user_management.html'
    context_object_name = 'users'
    
    def get_queryset(self):
        queryset = User.objects.select_related('department').all()
        
        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by department
        dept = self.request.GET.get('department')
        if dept:
            queryset = queryset.filter(department_id=dept)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search)
            )
        
        return queryset.order_by('department__name', 'role', 'username')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'User Management'
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['role_choices'] = [
            ('super_admin', 'Super Admin'),
            ('admin', 'Admin'),
            ('hod', 'Head of Department'),
            ('initiator', 'Initiator'),
        ]
        return context


class SuperAdminUserCreateView(SuperAdminRequiredMixin, CreateView):
    """Create new user - Super Admin only"""
    model = User
    form_class = SuperAdminUserCreationForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_management')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create User'
        context['is_create'] = True
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        initial['role'] = self.request.GET.get('role', 'initiator')
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)


class SuperAdminUserUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Update existing user - Super Admin only"""
    model = User
    form_class = UserUpdateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_management')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update User'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)


class SuperAdminUserDeleteView(SuperAdminRequiredMixin, DeleteView):
    """Delete user - Super Admin only"""
    model = User
    template_name = 'core/user_confirm_delete.html'
    success_url = reverse_lazy('core:user_management')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete User'
        return context
    
    def form_valid(self, form):
        user = self.get_object()
        messages.success(self.request, f'User {user.get_full_name()} has been deleted.')
        return super().form_valid(form)


@login_required
def toggle_user_status(request, pk):
    """Toggle user active status - Super Admin only"""
    if not request.user.is_super_admin:
        messages.error(request, 'Permission denied.')
        return redirect('core:user_management')
    
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, 'Cannot change your own status.')
        return redirect('core:user_management')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'activate':
            user.is_active = True
            messages.success(request, f'User {user.get_full_name()} has been activated.')
        elif action == 'deactivate':
            user.is_active = False
            messages.success(request, f'User {user.get_full_name()} has been deactivated.')
        user.save()
    
    return redirect('core:user_management')


class MaterialsManagementView(AdminRequiredMixin, TemplateView):
    """Materials Management for Admin and Super Admin"""
    template_name = 'core/materials_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Materials Management'
        
        # Get items with statistics
        items = Item.objects.select_related('location').all()
        context['total_items'] = items.count()
        context['active_items'] = items.filter(is_active=True).count()
        context['inactive_items'] = items.filter(is_active=False).count()
        context['low_stock_items'] = items.filter(
            is_active=True
        ).filter(models.Q(quantity_total__lte=models.F('reorder_level'))).count()
        
        # Recent items
        context['recent_items'] = items.order_by('-created_at')[:10]
        
        # By type
        context['stationery_count'] = items.filter(item_type='stationery').count()
        context['housekeeping_count'] = items.filter(item_type='housekeeping').count()
        
        # Locations
        from inventory.models import Location
        context['locations'] = Location.objects.all()
        
        return context


@login_required
def upload_items_excel(request):
    """Upload items from Excel file - Super Admin only"""
    from django.http import JsonResponse
    import pandas as pd
    from django.conf import settings
    import os
    
    if not request.user.is_super_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)
        
        file = request.FILES['file']
        
        # Validate file extension
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            return JsonResponse({'success': False, 'error': 'Only Excel or CSV files are allowed'}, status=400)
        
        # Read the file
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Validate required columns
        required_columns = ['material_code', 'description', 'item_type', 'unit_of_measurement', 'quantity_total']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return JsonResponse({
                'success': False, 
                'error': f'Missing required columns: {", ".join(missing_columns)}'
            }, status=400)
        
        # Process each row
        created_count = 0
        updated_count = 0
        errors = []
        
        from inventory.models import Location
        locations = {loc.code: loc for loc in Location.objects.all()}
        
        for index, row in df.iterrows():
            try:
                material_code = str(row['material_code']).strip()
                description = str(row['description']).strip()
                item_type = str(row['item_type']).strip().lower()
                uom = str(row['unit_of_measurement']).strip()
                quantity_total = int(row['quantity_total'])
                reorder_level = int(row.get('reorder_level', 10))
                location_code = str(row.get('location', '')).strip()
                
                # Find location if provided
                location = None
                if location_code and location_code.lower() != 'nan':
                    location = locations.get(location_code)
                
                # Create or update item
                item, created = Item.objects.update_or_create(
                    material_code=material_code,
                    defaults={
                        'description': description,
                        'item_type': item_type,
                        'unit_of_measurement': uom,
                        'quantity_total': quantity_total,
                        'reorder_level': reorder_level,
                        'location': location,
                        'is_active': True,
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
                # Create initial transaction
                if created:
                    Transaction.objects.create(
                        item=item,
                        user=request.user,
                        transaction_type='inward',
                        quantity_change=quantity_total,
                        balance_after=quantity_total,
                        reference='Excel Upload',
                        notes=f'Initial stock from Excel upload'
                    )
                    
            except Exception as e:
                errors.append(f'Row {index + 2}: {str(e)}')
        
        message = f'Successfully processed: {created_count} created, {updated_count} updated.'
        if errors:
            message += f' Errors: {len(errors)} rows failed.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'created': created_count,
            'updated': updated_count,
            'errors': errors[:10] if errors else []  # Limit errors to 10
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


class DepartmentManagementView(SuperAdminRequiredMixin, ListView):
    """Department Management for Super Admin"""
    model = Department
    template_name = 'core/department_management.html'
    context_object_name = 'departments'
    
    def get_queryset(self):
        return Department.objects.annotate(
            user_count=Count('users'),
            requisition_count=Count('users__requisitions', distinct=True)
        ).order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Department Management'
        return context


class DepartmentCreateUpdateView(SuperAdminRequiredMixin, UpdateView):
    """Create/Update departments - Super Admin only"""
    model = Department
    form_class = DepartmentForm
    template_name = 'core/department_form.html'
    success_url = reverse_lazy('core:department_management')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Department' if not self.object else 'Update Department'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Department saved successfully!')
        return super().form_valid(form)


class DepartmentDeleteView(SuperAdminRequiredMixin, UpdateView):
    """Delete department - Super Admin only"""
    model = Department
    template_name = 'core/department_confirm_delete.html'
    success_url = reverse_lazy('core:department_management')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Department'
        return context
    
    def delete(self, request, *args, **kwargs):
        dept = self.get_object()
        messages.success(request, f'Department {dept.name} has been deleted.')
        return super().delete(request, *args, **kwargs)


# Notification Views

@login_required
def notifications_list(request):
    """List all notifications for current user"""
    notifications = request.user.notifications.all()[:50]
    return render(request, 'core/notifications.html', {
        'title': 'Notifications',
        'notifications': notifications
    })


@login_required
def notifications_api(request):
    """API endpoint for getting notifications"""
    from django.http import JsonResponse
    
    notifications = request.user.notifications.filter(is_read=False)[:10]
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'link': n.link,
        'icon': n.get_icon(),
        'created_at': n.created_at.strftime('%b %d, %Y %H:%M'),
        'is_read': n.is_read
    } for n in notifications]
    
    return JsonResponse({
        'notifications': data,
        'unread_count': request.user.get_unread_notifications_count()
    })


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read"""
    from django.http import JsonResponse
    
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    from django.http import JsonResponse
    
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


# Helper function to create notifications
def create_notification(user, notification_type, title, message, link=None):
    """Helper function to create a notification"""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )

