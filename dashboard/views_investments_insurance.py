from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from banking.models_investments_insurance import InvestmentAccount, Investment, InsurancePolicy, InsuranceClaim

@login_required
def investments(request):
    """View all investment accounts and their investments"""
    investment_accounts = InvestmentAccount.objects.filter(user=request.user, is_active=True)
    total_investments = investment_accounts.aggregate(total=Sum('balance'))['total'] or 0
    
    context = {
        'active_tab': 'investments',
        'investment_accounts': investment_accounts,
        'total_investments': total_investments,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/investments_content.html', context)
    
    return render(request, 'dashboard/investments.html', context)

@login_required
def investment_detail(request, account_id):
    """View details of a specific investment account"""
    account = get_object_or_404(InvestmentAccount, id=account_id, user=request.user)
    investments = account.investments.all()
    
    context = {
        'active_tab': 'investments',
        'account': account,
        'investments': investments,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/investment_detail_content.html', context)
    
    return render(request, 'dashboard/investment_detail.html', context)

@login_required
def insurance(request):
    """View all insurance policies"""
    active_policies = InsurancePolicy.objects.filter(user=request.user, is_active=True)
    
    context = {
        'active_tab': 'insurance',
        'active_policies': active_policies,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/insurance_content.html', context)
    
    return render(request, 'dashboard/insurance.html', context)

@login_required
def insurance_policy_detail(request, policy_id):
    """View details of a specific insurance policy"""
    policy = get_object_or_404(InsurancePolicy, id=policy_id, user=request.user)
    claims = policy.claims.all().order_by('-claim_date')
    
    context = {
        'active_tab': 'insurance',
        'policy': policy,
        'claims': claims,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/insurance_policy_detail_content.html', context)
    
    return render(request, 'dashboard/insurance_policy_detail.html', context)
