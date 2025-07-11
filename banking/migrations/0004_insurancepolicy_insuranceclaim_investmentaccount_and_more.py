# Generated by Django 5.2.1 on 2025-06-01 11:59

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('banking', '0003_biller_billpayment_loanapplication_loanaccount_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InsurancePolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_type', models.CharField(choices=[('life', 'Life Insurance'), ('health', 'Health Insurance'), ('auto', 'Auto Insurance'), ('homeowners', 'Homeowners Insurance'), ('renters', 'Renters Insurance'), ('disability', 'Disability Insurance')], max_length=20)),
                ('policy_number', models.CharField(max_length=50, unique=True)),
                ('provider', models.CharField(max_length=100)),
                ('coverage_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('monthly_premium', models.DecimalField(decimal_places=2, max_digits=10)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insurance_policies', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='InsuranceClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claim_number', models.CharField(max_length=50, unique=True)),
                ('claim_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('description', models.TextField()),
                ('incident_date', models.DateField()),
                ('claim_date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('in_review', 'In Review'), ('approved', 'Approved'), ('denied', 'Denied'), ('paid', 'Paid')], default='submitted', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='claims', to='banking.insurancepolicy')),
            ],
        ),
        migrations.CreateModel(
            name='InvestmentAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_type', models.CharField(choices=[('brokerage', 'Brokerage Account'), ('ira', 'Individual Retirement Account (IRA)'), ('roth_ira', 'Roth IRA'), ('401k', '401(k)'), ('sep_ira', 'SEP IRA')], max_length=20)),
                ('account_number', models.CharField(max_length=20, unique=True)),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investment_accounts', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('investment_type', models.CharField(choices=[('stock', 'Stocks'), ('bond', 'Bonds'), ('mutual_fund', 'Mutual Funds'), ('etf', 'Exchange-Traded Funds (ETFs)'), ('cd', 'Certificates of Deposit (CDs)'), ('real_estate', 'Real Estate')], max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('symbol', models.CharField(blank=True, max_length=20, null=True)),
                ('quantity', models.DecimalField(decimal_places=6, default=0, max_digits=15)),
                ('purchase_price', models.DecimalField(decimal_places=2, max_digits=15)),
                ('current_price', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('purchase_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investments', to='banking.investmentaccount')),
            ],
        ),
    ]
