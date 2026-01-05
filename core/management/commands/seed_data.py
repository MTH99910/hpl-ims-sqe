#!/usr/bin/env python
"""
Django management command to generate dummy data for HPL Inventory Management System
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

from core.models import Department
from inventory.models import Item, Location, Transaction
from requisition.models import Requisition, RequisitionLineItem


User = get_user_model()


class Command(BaseCommand):
    help = 'Generates dummy data for HPL Inventory Management System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of users to create per department'
        )
        parser.add_argument(
            '--items',
            type=int,
            default=30,
            help='Number of items to create'
        )
        parser.add_argument(
            '--requisitions',
            type=int,
            default=15,
            help='Number of requisitions to create'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Generating dummy data...'))
        
        # Create departments
        self.create_departments()
        
        # Create locations
        self.create_locations()
        
        # Create users
        self.create_users(options['users'])
        
        # Create items
        self.create_items(options['items'])
        
        # Create transactions
        self.create_transactions()
        
        # Create requisitions
        self.create_requisitions(options['requisitions'])
        
        self.stdout.write(self.style.SUCCESS('Dummy data generation completed!'))
        self.stdout.write(self.style.WARNING('\nDefault Login Credentials:'))
        self.stdout.write(self.style.HTTP_INFO('  Super Admin: superadmin / admin123'))
        self.stdout.write(self.style.HTTP_INFO('  Admin: admin / admin123'))
        self.stdout.write(self.style.HTTP_INFO('  HOD (HR): hod_hr / admin123'))
        self.stdout.write(self.style.HTTP_INFO('  Initiator: user_hr_1 / admin123'))

    def create_departments(self):
        """Create departments"""
        departments = [
            ('HR', 'Human Resources'),
            ('IT', 'Information Technology'),
            ('Finance', 'Finance & Accounts'),
            ('Operations', 'Operations'),
            ('Admin', 'Administration'),
        ]
        
        created = 0
        for code, name in departments:
            dept, created_flag = Department.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
            if created_flag:
                created += 1
        
        self.stdout.write(f'  Created {created} departments')

    def create_locations(self):
        """Create warehouse locations"""
        locations = [
            ('1', 'Rack A - Shelf 1'),
            ('2', 'Rack A - Shelf 2'),
            ('3', 'Rack B - Shelf 1'),
            ('4', 'Rack B - Shelf 2'),
            ('5', 'Rack C - Shelf 1'),
        ]
        
        created = 0
        for code, name in locations:
            loc, created_flag = Location.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
            if created_flag:
                created += 1
        
        self.stdout.write(f'  Created {created} locations')

    def create_users(self, users_per_dept):
        """Create users with different roles"""
        departments = list(Department.objects.filter(is_active=True))
        
        # Create Super Admin user
        super_admin, created = User.objects.get_or_create(
            username='superadmin',
            defaults={
                'email': 'superadmin@hpl.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'role': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            super_admin.set_password('admin123')
            super_admin.save()
            self.stdout.write(f'  Created super admin user: superadmin/admin123')
        
        # Create Admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@hpl.com',
                'first_name': 'System',
                'last_name': 'Admin',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'  Created admin user: admin/admin123')
        
        # Create HOD users
        hod_password = 'admin123'
        for dept in departments:
            username = f"hod_{dept.code.lower()}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"hod.{dept.code.lower()}@hpl.com",
                    'first_name': f"HOD {dept.name.split()[0]}",
                    'last_name': 'Department',
                    'role': 'hod',
                    'department': dept,
                }
            )
            if created:
                user.set_password(hod_password)
                user.save()
                self.stdout.write(f'  Created HOD user: {username}/{hod_password}')
        
        # Create Initiator users
        initiator_password = 'admin123'
        for dept in departments:
            for i in range(1, users_per_dept + 1):
                username = f"user_{dept.code.lower()}_{i}"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f"user{i}.{dept.code.lower()}@hpl.com",
                        'first_name': f"User{i}",
                        'last_name': f"{dept.name.split()[0]}",
                        'role': 'initiator',
                        'department': dept,
                    }
                )
                if created:
                    user.set_password(initiator_password)
                    user.save()
        
        self.stdout.write(f'  Created {len(departments) * users_per_dept} initiator users per department')

    def create_items(self, count):
        """Create inventory items"""
        locations = list(Location.objects.all())
        
        stationery_items = [
            ('ST001', 'A4 Size Paper - 80 GSM (500 sheets per rim)', 'stationery', 'ream', 50),
            ('ST002', 'Ballpoint Pen - Blue (Box of 50)', 'stationery', 'box', 100),
            ('ST003', 'Ballpoint Pen - Black (Box of 50)', 'stationery', 'box', 100),
            ('ST004', 'Ballpoint Pen - Red (Box of 50)', 'stationery', 'box', 50),
            ('ST005', 'Stapler - Heavy Duty (Desktop)', 'stationery', 'pcs', 25),
            ('ST006', 'Staple Pins - 24/6 (Box of 1000)', 'stationery', 'box', 200),
            ('ST007', 'Paper Clips - Metal (Box of 100)', 'stationery', 'box', 150),
            ('ST008', 'File Folder - Manila (A4 Size, 100 per bundle)', 'stationery', 'pack', 75),
            ('ST009', 'Whiteboard Marker - Black (Box of 12)', 'stationery', 'box', 40),
            ('ST010', 'Whiteboard Marker - Blue (Box of 12)', 'stationery', 'box', 40),
            ('ST011', 'Correction Tape - Standard (Each)', 'stationery', 'pcs', 60),
            ('ST012', 'Scissors - Office (8 inch)', 'stationery', 'pcs', 30),
            ('ST013', 'Calculator - Desktop (12 Digit)', 'stationery', 'pcs', 20),
            ('ST014', 'Sticky Notes - Yellow (12 pads per pack)', 'stationery', 'pack', 80),
            ('ST015', 'Highlighters - Assorted Colors (6 per pack)', 'stationery', 'pack', 45),
        ]
        
        housekeeping_items = [
            ('HK001', 'Toilet Paper - Premium (12 rolls per pack)', 'housekeeping', 'pack', 100),
            ('HK002', 'Hand Towel Paper - Interfold (250 sheets per pack)', 'housekeeping', 'pack', 80),
            ('HK003', 'Liquid Hand Soap - 500ml bottle', 'housekeeping', 'bottle', 60),
            ('HK004', 'Floor Cleaner - 1 Liter bottle', 'housekeeping', 'bottle', 40),
            ('HK005', 'Disinfectant Spray - 400ml can', 'housekeeping', 'bottle', 50),
            ('HK006', 'Air Freshener - 300ml can', 'housekeeping', 'bottle', 35),
            ('HK007', 'Garbage Bags - Large (100 per pack)', 'housekeeping', 'pack', 70),
            ('HK008', 'Cleaning Cloths - Microfiber (5 per pack)', 'housekeeping', 'pack', 45),
            ('HK009', 'Mop Head - Cotton (Each)', 'housekeeping', 'pcs', 25),
            ('HK010', 'Bucket - Plastic 20 Liter', 'housekeeping', 'pcs', 15),
            ('HK011', 'Broom - Medium size (Each)', 'housekeeping', 'pcs', 20),
            ('HK012', 'Dustbin - Plastic 10 Liter', 'housekeeping', 'pcs', 30),
            ('HK013', 'Tissue Box - Facial (100 per box)', 'housekeeping', 'box', 90),
            ('HK014', 'Hand Gloves - Rubber (Pair)', 'housekeeping', 'pcs', 50),
            ('HK015', 'Trash Can Liners - Clear (50 per roll)', 'housekeeping', 'roll', 55),
        ]
        
        all_items = stationery_items + housekeeping_items
        
        created = 0
        for i, (code, desc, item_type, uom, qty) in enumerate(all_items):
            item, created_flag = Item.objects.get_or_create(
                material_code=code,
                defaults={
                    'description': desc,
                    'item_type': item_type,
                    'unit_of_measurement': uom,
                    'location': random.choice(locations) if locations else None,
                    'quantity_total': qty,
                    'reorder_level': max(5, qty // 4),
                    'is_active': True,
                }
            )
            if created_flag:
                created += 1
        
        self.stdout.write(f'  Created {created} inventory items (15 Stationery + 15 Housekeeping)')

    def create_transactions(self):
        """Create initial stock transactions"""
        items = Item.objects.all()
        
        created = 0
        for item in items:
            # Create initial inward transaction
            Transaction.objects.create(
                item=item,
                user_id=1,  # Admin user
                transaction_type='inward',
                quantity_change=item.quantity_total,
                balance_after=item.quantity_total,
                reference='Initial Stock',
                notes=f'Initial stock setup for {item.material_code}'
            )
            created += 1
        
        self.stdout.write(f'  Created {created} initial stock transactions')

    def create_requisitions(self, count):
        """Create sample requisitions"""
        departments = Department.objects.filter(is_active=True)
        initiators = list(User.objects.filter(role='initiator'))
        hods = list(User.objects.filter(role='hod'))
        items = list(Item.objects.filter(is_active=True))
        
        if not initiators or not items:
            self.stdout.write(self.style.WARNING('  Skipping requisition creation (no users or items)'))
            return
        
        created = 0
        statuses = ['pending_hod', 'authorized', 'issued']
        
        for i in range(count):
            initiator = random.choice(initiators)
            hod_candidates = [h for h in hods if h.department == initiator.department]
            hod = hod_candidates[0] if hod_candidates else None
            
            # Random number of items per requisition (1-5)
            num_items = random.randint(1, min(5, len(items)))
            selected_items = random.sample(items, num_items)
            
            # Create requisition
            req = Requisition.objects.create(
                requisition_number=f'REQ-{timezone.now().strftime("%Y%m%d")}-{i+1:04d}',
                initiator=initiator,
                purpose=f'Requisition for {initiator.department.name} department operations',
                status=random.choice(statuses),
            )
            
            if hod:
                req.hod_approver = hod
                if req.status in ['authorized', 'issued']:
                    req.hod_action_date = timezone.now() - timedelta(days=random.randint(0, 3))
            
            if req.status == 'issued':
                admin = User.objects.filter(role='admin').first()
                if admin:
                    req.issuer = admin
                req.issued_date = timezone.now() - timedelta(days=random.randint(0, 2))
            
            req.save()
            
            # Create line items
            for item in selected_items:
                qty_requested = random.randint(1, min(10, item.quantity_total))
                qty_issued = 0
                
                if req.status == 'issued':
                    qty_issued = random.randint(1, qty_requested)
                    # Update item stock
                    item.quantity_total -= qty_issued
                    item.save()
                    
                    # Create transaction
                    Transaction.objects.create(
                        item=item,
                        user=req.issuer,
                        transaction_type='outward',
                        quantity_change=-qty_issued,
                        balance_after=item.quantity_total,
                        reference=req.requisition_number,
                        notes=f'Issued via requisition {req.requisition_number}'
                    )
                
                RequisitionLineItem.objects.create(
                    requisition=req,
                    item=item,
                    quantity_requested=qty_requested,
                    quantity_issued=qty_issued,
                    uom=item.unit_of_measurement,
                )
            
            created += 1
        
        self.stdout.write(f'  Created {created} sample requisitions')
