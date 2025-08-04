from functools import wraps
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
import requests
import json
from integration_utils.bitrix24.bitrix_user_auth.main_auth import main_auth
import bitrix_app.urls


@main_auth(on_start=True, set_cookie=True)
def start(request):
    context = {
        'user_first_name': request.bitrix_user.first_name,
        'user_last_name': request.bitrix_user.last_name,
    }

    return render(request, 'main/index.html', context)
@main_auth(on_cookies= True)
def index(request):
    print(dir(request))
    print(type(request.bitrix_user))

    context = {
        'user_first_name': request.bitrix_user.first_name,
        'user_last_name': request.bitrix_user.last_name,
    }

    return render(request, 'main/index.html', context)

@main_auth(on_cookies= True)
def last_active_deals(request):
    auth_token = request.bitrix_user_token.auth_token
    print('auth_token:', auth_token)
    deals = []
    error = None
    deals = request.bitrix_user_token.call_api_method(
        api_method='crm.deal.list',
        params={
            'auth': auth_token,
            'order': {'DATE_CREATE': 'DESC'},
            'filter': {
                '!@STAGE_ID': ['WON', 'LOSE', 'APOLOGY']
            },
            'select': ['ID','STAGE_ID', 'TITLE', 'DATE_CREATE', 'OPPORTUNITY', 'UF_CRM_1754146731437']
        }
    )['result'][:10]

    for deal in deals:
        if deal['UF_CRM_1754146731437']=='1':
            deal['UF_CRM_1754146731437'] = 'Да'
        else:
            deal['UF_CRM_1754146731437'] = 'Нет'

    return render(request, 'main/last_active_deals.html', {
        'deals': deals,
        'error': error
    })


@main_auth(on_cookies= True)
def add_deal(request):
    if request.method == 'POST':
        auth_token = request.bitrix_user_token.auth_token
        loyal_value='0'
        if request.POST.get('loyal')=='on':
            loyal_value='1'
        
        request.bitrix_user_token.call_api_method(
            api_method='crm.deal.add',
            params={
                'auth': auth_token,
                'fields': {
                    'TITLE': request.POST.get('title'),
                    'STAGE_ID': request.POST.get('stage_id'),
                    'OPPORTUNITY': request.POST.get('amount'),
                    'UF_CRM_1754146731437': loyal_value,
                }
            }
        )
        return redirect('main:last_active_deals')

    return render(request, 'main/add_deal.html')